"""menu_assistant.worker.worker_app.rag.retrieval

역할(통합본):
- ChromaDB(menu_index)에서 표준 메뉴 후보를 검색한다.
- (FAST PATH) Step3의 menu_name_norm(variants)와 Chroma metadata(menu/variants)가 정확히 일치하면
  즉시 CONFIRMED로 판정한다.
- 그 외에는 후보 점수를 융합해(CONFIRMED/AMBIGUOUS/NOT_FOUND) 상태를 판정한다.

이 모듈은 "RAG 매칭"에 필요한 로직을 모두 포함합니다.
- Step04(step_04_rag_match.py)는 I/O(파일 읽기/쓰기)와 호출만 담당합니다.

주의:
- 사용자 알러지 위험도(DANGER/CAUTION/SAFE), LLM 호출은 다른 모듈로 분리합니다.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions


# ==============================
# CONFIG
# ==============================
COLLECTION_NAME = "menu_index"
DEFAULT_TOP_K = 20
DEFAULT_RERANK_TOP_K = 5
DEFAULT_SCORE_THRESHOLD = 0.55
DEFAULT_AMBIGUOUS_GAP = 0.03

# Chroma persist dir (프로젝트 상대경로)
BASE_DIR = Path(__file__).resolve().parents[3]  # menu_assistant/
DEFAULT_CHROMA_DIR = BASE_DIR / "data" / "chroma"

# Embedding model (index 빌드와 동일해야 함)
DEFAULT_EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# jaccard tuning
DEFAULT_MIN_JACCARD = 0.10
WEIGHT_EMBED = 0.55
WEIGHT_RERANK = 0.25
WEIGHT_JACCARD = 0.10
WEIGHT_MENU_BONUS = 0.10

# ------------------------------
# ENV OVERRIDES (orchestrator에서 주입)
# ------------------------------
ENV_CHROMA_DIR = "MENU_ASSISTANT_CHROMA_DIR"
ENV_COLLECTION = "MENU_ASSISTANT_COLLECTION"
ENV_EMBED_MODEL = "MENU_ASSISTANT_EMBED_MODEL"


# ==============================
# DATA STRUCTURES
# ==============================
@dataclass
class Candidate:
    id: str
    score: float  # similarity (1.0에 가까울수록 좋음)
    menu: str
    variants: List[str]
    ingredients_ko: List[str]
    alg_tags: List[str]
    source: str = ""


@dataclass
class RetrievalResult:
    status: str  # CONFIRMED | AMBIGUOUS | NOT_FOUND
    best_match: Optional[Candidate]
    candidates: List[Candidate]
    used_query: Optional[str] = None
    debug: Optional[Dict[str, Any]] = None


# ==============================
# UTILS
# ==============================
_WS_RE = re.compile(r"\s+")
_SLASH_SPLIT_RE = re.compile(r"\s*/\s*")


def _get_env_path(name: str) -> Optional[Path]:
    v = os.environ.get(name)
    if not v:
        return None
    try:
        return Path(v).expanduser().resolve()
    except Exception:
        return Path(v)


def _norm_space(s: str) -> str:
    s = (s or "").strip()
    s = _WS_RE.sub(" ", s)
    return s


def _split_csv(s: str) -> List[str]:
    if not s:
        return []
    parts = [p.strip() for p in str(s).split(",")]
    return [p for p in parts if p]


def _parse_metadata(md: Dict[str, Any]) -> Tuple[str, List[str], List[str], List[str], str]:
    menu = _norm_space(str(md.get("menu", "")))
    variants = _split_csv(md.get("variants", ""))
    ingredients = _split_csv(md.get("ingredients_ko", ""))
    alg_tags = _split_csv(md.get("alg_tags", ""))
    source = _norm_space(str(md.get("source", "")))
    return menu, variants, ingredients, alg_tags, source


def _safe_get_first(lst: Any, default=None):
    if isinstance(lst, list) and lst:
        return lst[0]
    return default


def _to_similarity(distance: Optional[float]) -> float:
    if distance is None:
        return 0.0
    try:
        d = float(distance)
    except Exception:
        return 0.0
    return 1.0 - d


def _expand_variants(variants: List[str]) -> List[str]:
    out: List[str] = []
    for v in variants or []:
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


def _char_ngram(s: str, n: int = 2) -> set:
    s = _norm_space(s)
    if not s:
        return set()
    if len(s) < n:
        return {s}
    return {s[i : i + n] for i in range(len(s) - n + 1)}


def _jaccard(a: str, b: str, n: int = 2) -> float:
    first = _char_ngram(a, n)
    second = _char_ngram(b, n)
    if not first or not second:
        return 0.0
    return len(first & second) / len(first | second)


def _candidate_keys(c: Candidate) -> List[str]:
    keys: List[str] = []
    if c.menu:
        keys.append(_norm_space(c.menu))
    for v in c.variants or []:
        vv = _norm_space(v)
        if vv:
            keys.append(vv)
    # dedup preserve order
    seen = set()
    out: List[str] = []
    for k in keys:
        if k and k not in seen:
            out.append(k)
            seen.add(k)
    return out


def _build_jaccard_pool(c: Candidate) -> List[str]:
    pool: List[str] = []
    pool.extend(_candidate_keys(c))
    for ing in c.ingredients_ko or []:
        ii = _norm_space(ing)
        if ii:
            pool.append(ii)
    seen = set()
    out: List[str] = []
    for x in pool:
        if x and x not in seen:
            out.append(x)
            seen.add(x)
    return out


def _max_jaccard(query: str, pool: List[str]) -> float:
    q = _norm_space(query)
    if not q:
        return 0.0
    best = 0.0
    for t in pool:
        best = max(best, _jaccard(q, t, n=2))
    return float(best)


def _menu_jaccard_bonus(menu_jaccard: str, cand: Candidate) -> float:
    mj = _norm_space(menu_jaccard)
    if not mj:
        return 0.0

    menu = _norm_space(cand.menu)
    vlist = [_norm_space(x) for x in (cand.variants or []) if _norm_space(x)]
    ilist = [_norm_space(x) for x in (cand.ingredients_ko or []) if _norm_space(x)]

    # 1) substring match (menu/variants)
    sub_hit = 0.0
    if mj and menu and mj in menu:
        sub_hit = 1.0
    else:
        for v in vlist:
            if v and mj in v:
                sub_hit = 1.0
                break

    # 2) ingredients substring
    ing_hit = 0.0
    for ing in ilist:
        if ing and mj in ing:
            ing_hit = 1.0
            break

    # 3) jaccard to menu and to joined ingredients
    jac_menu = _jaccard(mj, menu) if menu else 0.0
    jac_ing = _jaccard(mj, " ".join(ilist)) if ilist else 0.0

    bonus = 0.55 * sub_hit + 0.20 * ing_hit + 0.15 * jac_menu + 0.10 * jac_ing
    return max(0.0, min(1.0, float(bonus)))


def _try_import_rerank():
    try:
        from menu_assistant.worker.worker_app.rag.rerank import rerank_candidates, RerankConfig

        return rerank_candidates, RerankConfig
    except Exception:
        return None, None


# ==============================
# CHROMA RETRIEVER
# ==============================
class ChromaMenuRetriever:
    def __init__(
        self,
        chroma_dir: Path = DEFAULT_CHROMA_DIR,
        collection_name: str = COLLECTION_NAME,
        embed_model: str = DEFAULT_EMBED_MODEL,
    ):
        self.chroma_dir = _get_env_path(ENV_CHROMA_DIR) or Path(chroma_dir)
        self.collection_name = os.environ.get(ENV_COLLECTION) or collection_name
        self.embed_model = os.environ.get(ENV_EMBED_MODEL) or embed_model
        self._client = None
        self._collection = None

    def _init(self):
        if self._collection is not None:
            return
        if not self.chroma_dir.exists():
            raise RuntimeError(
                f"[RAG] chroma_dir does not exist: {self.chroma_dir} (set env {ENV_CHROMA_DIR})"
            )

        emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=self.embed_model)

        if hasattr(chromadb, "PersistentClient"):
            self._client = chromadb.PersistentClient(path=str(self.chroma_dir))
        else:
            self._client = chromadb.Client(
                Settings(persist_directory=str(self.chroma_dir), anonymized_telemetry=False)
            )

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=emb_fn,
        )

        print(f"[RAG] chroma_dir = {self.chroma_dir}")
        print(f"[RAG] collection = {self.collection_name}")
        try:
            cnt = self._collection.count()
        except Exception:
            got = self._collection.get(limit=1, include=["metadatas"])
            cnt = len(got.get("ids", []))
        print(f"[RAG] collection.count() = {cnt}")
        if cnt == 0:
            raise RuntimeError(
                f"[RAG] collection is empty. chroma_dir={self.chroma_dir} collection={self.collection_name}"
            )

    @property
    def collection(self):
        self._init()
        return self._collection

    def _exact_match_by_menu(self, query: str, limit: int) -> List[Candidate]:
        query = _norm_space(query)
        if not query:
            return []
        raw = None
        try:
            raw = self.collection.get(where={"menu": query}, limit=limit, include=["metadatas", "ids"])
        except TypeError:
            try:
                raw = self.collection.get(where={"menu": query})
            except Exception:
                return []
        except Exception:
            return []

        if not isinstance(raw, dict):
            return []

        ids = raw.get("ids") or []
        metadatas = raw.get("metadatas") or []

        # 2D normalize
        if isinstance(ids, list) and ids and isinstance(ids[0], list):
            ids = ids[0]
        if isinstance(metadatas, list) and metadatas and isinstance(metadatas[0], list):
            metadatas = metadatas[0]

        out: List[Candidate] = []
        for _id, md in zip(ids, metadatas):
            menu, vars_, ing, tags, source = _parse_metadata(md or {})
            out.append(
                Candidate(
                    id=str(_id),
                    score=1.0,
                    menu=menu,
                    variants=vars_,
                    ingredients_ko=ing,
                    alg_tags=tags,
                    source=source,
                )
            )
        return out

    def _query_once(self, query: str, top_k: int) -> List[Candidate]:
        query = _norm_space(query)
        if not query:
            return []

        raw = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["metadatas", "distances"],
        )

        ids = _safe_get_first(raw.get("ids"), [])
        metadatas = _safe_get_first(raw.get("metadatas"), [])
        distances = _safe_get_first(raw.get("distances"), [])

        if not ids:
            ids = [f"idx_{i}" for i in range(len(metadatas))]

        out: List[Candidate] = []
        for _id, md, dist in zip(ids, metadatas, distances):
            menu, vars_, ing, tags, source = _parse_metadata(md or {})
            out.append(
                Candidate(
                    id=str(_id),
                    score=float(_to_similarity(dist)),
                    menu=menu,
                    variants=vars_,
                    ingredients_ko=ing,
                    alg_tags=tags,
                    source=source,
                )
            )
        out.sort(key=lambda x: x.score, reverse=True)
        return out

    def retrieve_candidates_for_variants(
        self,
        variants: List[str],
        top_k: int,
        include_debug: bool,
    ) -> Tuple[Optional[str], List[Candidate], Optional[Dict[str, Any]]]:
        variants = _expand_variants([_norm_space(v) for v in (variants or [])])
        variants = [v for v in variants if v]

        if not variants:
            dbg = {"reason": "empty_variants"} if include_debug else None
            return None, [], dbg

        best_query: Optional[str] = None
        best_candidates: List[Candidate] = []
        best_score = -1.0
        debug: Optional[Dict[str, Any]] = {"per_query": []} if include_debug else None

        for q in variants:
            # exact(menu==q) 우선
            cands = self._exact_match_by_menu(q, limit=top_k)
            mode = "exact" if cands else "embed"
            if not cands:
                cands = self._query_once(q, top_k=top_k)

            if include_debug and debug is not None:
                debug["per_query"].append(
                    {
                        "query": q,
                        "mode": mode,
                        "top_scores": [c.score for c in cands[: min(5, len(cands))]],
                        "top_menus": [c.menu for c in cands[: min(5, len(cands))]],
                    }
                )

            if not cands:
                continue
            if cands[0].score > best_score:
                best_score = cands[0].score
                best_query = q
                best_candidates = cands

        return best_query, best_candidates, debug


# ==============================
# RAG MATCH (PUBLIC)
# ==============================
_DEFAULT_RETRIEVER: Optional[ChromaMenuRetriever] = None


def get_retriever() -> ChromaMenuRetriever:
    global _DEFAULT_RETRIEVER
    if _DEFAULT_RETRIEVER is None:
        _DEFAULT_RETRIEVER = ChromaMenuRetriever()
    return _DEFAULT_RETRIEVER


def match_menu_item(
    variants: List[str],
    menu_jaccard: str = "",
    detail_parts_norm: Optional[List[str]] = None,
    is_set: Optional[bool] = None,
    top_k: int = DEFAULT_TOP_K,
    rerank_top_k: int = DEFAULT_RERANK_TOP_K,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
    ambiguous_gap: float = DEFAULT_AMBIGUOUS_GAP,
    use_rerank: bool = True,
    include_debug: bool = False,
    min_jaccard: float = DEFAULT_MIN_JACCARD,
) -> Dict[str, Any]:
    """Step04에서 한 메뉴 항목에 대해 호출하는 통합 RAG 매칭 함수."""

    variants = _expand_variants([_norm_space(v) for v in (variants or [])])
    variants = [v for v in variants if v]

    retriever = get_retriever()
    used_query, candidates, dbg = retriever.retrieve_candidates_for_variants(
        variants=variants,
        top_k=int(top_k),
        include_debug=include_debug,
    )

    if not candidates:
        return {
            "status": "NOT_FOUND",
            "used_query": None,
            "best_match": None,
            "candidates": [],
            "debug": dbg,
        }

    # ------------------------------
    # 1) EXACT MATCH FAST PATH
    # ------------------------------
    qset = {_norm_space(v) for v in variants if _norm_space(v)}
    exact_idx: Optional[int] = None
    exact_key: Optional[str] = None

    for i, c in enumerate(candidates):
        for k in _candidate_keys(c):
            if k in qset:
                exact_idx = i
                exact_key = k
                break
        if exact_idx is not None:
            break

    if exact_idx is not None:
        best = candidates[exact_idx]
        # candidates 재정렬 (exact를 맨 앞으로)
        ordered = [best] + [c for j, c in enumerate(candidates) if j != exact_idx]

        best_dict = asdict(best)
        best_dict.update(
            {
                "embed_score": float(best.score),
                "rerank_score": 0.0,
                "_jaccard": 1.0,
                "_menu_bonus": 1.0,
                "final_score": 1.0,
                "_exact_match_key": exact_key,
            }
        )

        cand_dicts: List[Dict[str, Any]] = []
        for c in ordered:
            d = asdict(c)
            d.update(
                {
                    "embed_score": float(c.score),
                    "rerank_score": 0.0,
                    "_jaccard": 1.0 if c is best else 0.0,
                    "_menu_bonus": 1.0 if c is best else float(_menu_jaccard_bonus(menu_jaccard, c)),
                    "final_score": 1.0 if c is best else float(c.score),
                }
            )
            cand_dicts.append(d)

        debug_out = dbg if include_debug else None
        if include_debug:
            if debug_out is None:
                debug_out = {}
            debug_out.update({"reason": "exact_match", "exact_key": exact_key})

        return {
            "status": "CONFIRMED",
            "used_query": used_query,
            "best_match": best_dict,
            "candidates": cand_dicts,
            "debug": debug_out,
        }

    # ------------------------------
    # 2) SCORE FUSION (no hard jaccard filter)
    # ------------------------------
    cand_dicts: List[Dict[str, Any]] = []
    for c in candidates:
        pool = _build_jaccard_pool(c)
        jac = _max_jaccard(menu_jaccard, pool)
        if menu_jaccard and jac < float(min_jaccard):
            # 너무 공격적인 제거는 금지: score만 낮게 반영
            jac = float(jac)
        bonus = _menu_jaccard_bonus(menu_jaccard, c)
        cand_dicts.append(
            {
                **asdict(c),
                "embed_score": float(c.score),
                "rerank_score": 0.0,
                "_jaccard": float(jac),
                "_menu_bonus": float(bonus),
            }
        )

    # rerank (optional)
    if use_rerank:
        rerank_candidates, RerankConfig = _try_import_rerank()
        if rerank_candidates is not None:
            cfg = RerankConfig(keep_debug=include_debug)
            cand_dicts = rerank_candidates(
                candidates=cand_dicts,
                menu_name_variants_norm=variants,
                detail_parts_norm=list(detail_parts_norm or []),
                is_set=is_set,
                config=cfg,
                top_k=int(rerank_top_k),
            )

    # final score
    for d in cand_dicts:
        embed = float(d.get("embed_score", 0.0) or 0.0)
        rer = float(d.get("rerank_score", 0.0) or 0.0)
        jac = float(d.get("_jaccard", 0.0) or 0.0)
        mb = float(d.get("_menu_bonus", 0.0) or 0.0)
        d["final_score"] = WEIGHT_EMBED * embed + WEIGHT_RERANK * rer + WEIGHT_JACCARD * jac + WEIGHT_MENU_BONUS * mb

    cand_dicts.sort(key=lambda x: float(x.get("final_score", 0.0) or 0.0), reverse=True)

    best = cand_dicts[0] if cand_dicts else None
    if not best:
        return {
            "status": "NOT_FOUND",
            "used_query": used_query,
            "best_match": None,
            "candidates": [],
            "debug": dbg if include_debug else None,
        }

    best_score = float(best.get("final_score", 0.0) or 0.0)
    second_score = float(cand_dicts[1].get("final_score", 0.0) or 0.0) if len(cand_dicts) >= 2 else 0.0
    gap = best_score - second_score

    if best_score < float(score_threshold):
        status = "NOT_FOUND"
        best_out = None
    else:
        status = "CONFIRMED" if gap >= float(ambiguous_gap) else "AMBIGUOUS"
        best_out = best

    debug_out = dbg if include_debug else None
    if include_debug:
        if debug_out is None:
            debug_out = {}
        debug_out.update({"final_best": best_score, "final_second": second_score, "final_gap": gap})

    return {
        "status": status,
        "used_query": used_query,
        "best_match": best_out,
        "candidates": cand_dicts,
        "debug": debug_out,
    }


# ------------------------------
# Backward compatible API
# ------------------------------

def retrieve_menu(
    variants: List[str],
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
    ambiguous_gap: float = DEFAULT_AMBIGUOUS_GAP,
    include_debug: bool = False,
) -> Dict[str, Any]:
    """구버전 Step04 호환용. menu_jaccard/재료 기반 보정 없이 동작."""
    out = match_menu_item(
        variants=variants,
        menu_jaccard="",
        detail_parts_norm=None,
        is_set=None,
        top_k=top_k,
        rerank_top_k=DEFAULT_RERANK_TOP_K,
        score_threshold=score_threshold,
        ambiguous_gap=ambiguous_gap,
        use_rerank=False,
        include_debug=include_debug,
    )
    # 구버전 키 유지
    return {
        "status": out.get("status"),
        "used_query": out.get("used_query"),
        "best_match": out.get("best_match"),
        "candidates": out.get("candidates"),
        "debug": out.get("debug"),
    }
