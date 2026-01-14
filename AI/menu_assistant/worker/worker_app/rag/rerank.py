"""
menu_assistant.worker.worker_app.rag.rerank

역할:
- Chroma embedding top_k 후보(Candidate 리스트)를
  Step3 normalize 결과 신호(menu_name_variants_norm, detail_parts_norm, is_set 등)로 재정렬(rerank)한다.

설계:
- retrieval.py는 검색(retrieval)만 담당
- rerank.py는 후보 재정렬만 담당 (외부 의존성 최소화)

출력:
- rerank_candidates: 후보를 dict 리스트로 반환(정렬됨, rerank_score 포함)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

_WS_RE = re.compile(r"\s+")
_NON_KO_EN_NUM_RE = re.compile(r"[^0-9A-Za-z가-힣]+")
_DIGITS_RE = re.compile(r"\d+")
_SLASH_SPLIT_RE = re.compile(r"\s*/\s*")

GENERIC_BAD_WORDS = {
    "추가", "추가메뉴", "사이드", "사이드메뉴", "서비스", "할인", "행사",
    "음료", "음료수", "주류", "술", "소주", "맥주", "와인",
    "차", "커피", "물", "콜라", "사이다",
    "단품", "포장", "테이크아웃", "배달",
    "원산지", "안내", "공지",
}

SET_HINT_WORDS = {"세트", "정식", "모듬", "모둠", "코스"}


@dataclass
class RerankConfig:
    w_embed: float = 1.0
    w_exact: float = 0.40
    w_contain: float = 0.22
    w_seq: float = 0.18
    w_detail_hit: float = 0.10
    w_set_match: float = 0.08

    p_generic: float = 0.20
    p_too_short: float = 0.10

    clamp_min: float = 0.0
    clamp_max: float = 2.0

    keep_debug: bool = False


CandidateLike = Union[Dict[str, Any], Any]


def _norm_space(s: str) -> str:
    s = (s or "").strip()
    s = _WS_RE.sub(" ", s)
    return s


def _norm_compact(s: str) -> str:
    s = _norm_space(s)
    s = s.replace(" ", "")
    s = _NON_KO_EN_NUM_RE.sub("", s)
    return s


def _norm_token(s: str) -> str:
    s = _norm_compact(s)
    s = _DIGITS_RE.sub("", s)
    return s


def _expand_variants_norm(variants_norm: Iterable[str]) -> List[str]:
    out: List[str] = []
    for v in variants_norm or []:
        v = _norm_space(v)
        if not v:
            continue
        out.append(v)
        if "/" in v:
            for part in _SLASH_SPLIT_RE.split(v):
                part = _norm_space(part)
                if part and part not in out:
                    out.append(part)

    seen = set()
    uniq: List[str] = []
    for x in out:
        if x not in seen:
            uniq.append(x)
            seen.add(x)
    return uniq


def _seq_sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return float(SequenceMatcher(None, a, b).ratio())


def _has_generic_word(menu: str) -> bool:
    mc = _norm_compact(menu)
    for w in GENERIC_BAD_WORDS:
        if _norm_compact(w) in mc:
            return True
    return False


def _has_set_hint(menu: str) -> bool:
    mc = _norm_compact(menu)
    for w in SET_HINT_WORDS:
        if _norm_compact(w) in mc:
            return True
    return False


def _candidate_to_dict(c: CandidateLike) -> Dict[str, Any]:
    if isinstance(c, dict):
        return dict(c)
    d: Dict[str, Any] = {}
    for k in ["id", "score", "menu", "ingredients_ko", "alg_tags", "source"]:
        if hasattr(c, k):
            d[k] = getattr(c, k)
    return d


def _detail_overlap_score(detail_parts_norm: List[str], ingredients_ko: List[str]) -> Tuple[float, int]:
    if not detail_parts_norm or not ingredients_ko:
        return 0.0, 0

    ing_compacts = [_norm_compact(x) for x in ingredients_ko if x]
    ing_compacts = [x for x in ing_compacts if x]

    hits = 0
    used = set()
    for dp in detail_parts_norm:
        t = _norm_token(dp)
        if len(t) < 2:
            continue
        for ing in ing_compacts:
            if t in ing and (t, ing) not in used:
                hits += 1
                used.add((t, ing))
                break

    denom = min(max(len(detail_parts_norm), 1), 5)
    score = min(hits, 5) / float(denom)
    return float(score), hits


def _variants_lexical_score(variants_norm: List[str], candidate_menu: str) -> Dict[str, float]:
    if not variants_norm or not candidate_menu:
        return {"exact": 0.0, "contain": 0.0, "seq": 0.0}

    cand_c = _norm_compact(candidate_menu)
    best_exact = 0.0
    best_contain = 0.0
    best_seq = 0.0

    for v in variants_norm:
        vc = _norm_compact(v)
        if not vc:
            continue

        if vc == cand_c:
            best_exact = 1.0

        if vc in cand_c or cand_c in vc:
            best_contain = max(best_contain, 1.0)

        best_seq = max(best_seq, _seq_sim(vc, cand_c))

        if best_exact == 1.0 and best_contain == 1.0 and best_seq >= 0.98:
            break

    return {"exact": best_exact, "contain": best_contain, "seq": best_seq}


def rerank_candidates(
    candidates: List[CandidateLike],
    menu_name_variants_norm: List[str],
    detail_parts_norm: Optional[List[str]] = None,
    is_set: Optional[bool] = None,
    config: Optional[RerankConfig] = None,
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    cfg = config or RerankConfig()
    variants = _expand_variants_norm(menu_name_variants_norm or [])
    detail_parts = detail_parts_norm or []

    out: List[Dict[str, Any]] = []

    for c in candidates or []:
        cd = _candidate_to_dict(c)
        base = float(cd.get("score") or 0.0)

        menu = str(cd.get("menu") or "")
        ings = cd.get("ingredients_ko") or []
        if not isinstance(ings, list):
            ings = []

        lex = _variants_lexical_score(variants, menu)
        dscore, dhits = _detail_overlap_score(detail_parts, ings)

        set_bonus = 0.0
        if is_set is not None:
            cand_is_set_like = _has_set_hint(menu)
            if is_set and cand_is_set_like:
                set_bonus = 1.0
            elif (not is_set) and cand_is_set_like:
                set_bonus = -0.5

        penalty = 0.0
        mc = _norm_compact(menu)
        if _has_generic_word(menu):
            penalty += cfg.p_generic
        if len(mc) <= 2:
            penalty += cfg.p_too_short

        rerank_score = (
            cfg.w_embed * base
            + cfg.w_exact * lex["exact"]
            + cfg.w_contain * lex["contain"]
            + cfg.w_seq * lex["seq"]
            + cfg.w_detail_hit * dscore
            + cfg.w_set_match * set_bonus
            - penalty
        )

        rerank_score = max(cfg.clamp_min, min(cfg.clamp_max, rerank_score))
        cd["rerank_score"] = float(rerank_score)

        if cfg.keep_debug:
            cd["rerank_debug"] = {
                "base_embed": base,
                "lex": lex,
                "detail_overlap": {"score": dscore, "hits": dhits, "detail_parts": detail_parts},
                "set_bonus": set_bonus,
                "penalty": penalty,
                "menu_compact": mc,
            }

        out.append(cd)

    out.sort(key=lambda x: (x.get("rerank_score", 0.0), x.get("score", 0.0)), reverse=True)

    if top_k is not None:
        out = out[: int(top_k)]

    return out
