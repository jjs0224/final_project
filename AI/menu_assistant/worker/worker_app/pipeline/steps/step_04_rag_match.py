from __future__ import annotations

import argparse
import inspect
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from menu_assistant.worker.worker_app.rag.retrieval import retrieve_menu as retrieve_menu_fn
from menu_assistant.worker.worker_app.rag.rerank import rerank_candidates, RerankConfig


# -----------------------------
# Utils
# -----------------------------
_SLASH_SPLIT_RE = re.compile(r"\s*/\s*")
_WS_RE = re.compile(r"\s+")

SET_HINT_WORDS = ("세트", "정식", "모듬", "모둠", "코스")


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _resolve_run_dir(data_dir: Path, run_id: str) -> Path:
    return data_dir / "runs" / run_id


def _norm_space(s: str) -> str:
    s = (s or "").strip()
    s = _WS_RE.sub(" ", s)
    return s


def _expand_slash_variants(variants: List[str]) -> List[str]:
    out: List[str] = []
    for v in variants or []:
        v = _norm_space(str(v))
        if not v:
            continue
        out.append(v)
        if "/" in v:
            for p in _SLASH_SPLIT_RE.split(v):
                p = _norm_space(p)
                if p and p not in out:
                    out.append(p)

    seen = set()
    uniq: List[str] = []
    for x in out:
        if x not in seen:
            uniq.append(x)
            seen.add(x)
    return uniq


def _infer_is_set_from_text(text: str) -> bool:
    t = _norm_space(text)
    return any(w in t for w in SET_HINT_WORDS)


def _safe_list(v: Any) -> List[Any]:
    return v if isinstance(v, list) else []


# -----------------------------
# Retrieve wrapper (keeps compatibility with older retrieval.py)
# -----------------------------

def _call_retrieve_menu(
    variants: List[str],
    top_k: int,
    score_threshold: float,
    ambiguous_gap: float,
    include_debug: bool,
    use_rerank: bool,
    rerank_top_k: int,
    detail_parts_norm: Optional[List[str]],
    is_set: Optional[bool],
) -> Dict[str, Any]:
    """
    retrieval.retrieve_menu()가 rerank 파라미터를 지원하는지 런타임에 확인하고,
    지원하면 해당 파라미터를 전달합니다.
    지원하지 않으면(구버전 retrieval.py) 기본 파라미터만 전달합니다.
    """
    sig = inspect.signature(retrieve_menu_fn)
    params = set(sig.parameters.keys())

    kwargs: Dict[str, Any] = {
        "variants": variants,
        "top_k": top_k,
        "score_threshold": score_threshold,
        "ambiguous_gap": ambiguous_gap,
        "include_debug": include_debug,
    }

    if "use_rerank" in params:
        kwargs["use_rerank"] = use_rerank
    if "rerank_top_k" in params:
        kwargs["rerank_top_k"] = rerank_top_k
    if "detail_parts_norm" in params:
        kwargs["detail_parts_norm"] = detail_parts_norm
    if "is_set" in params:
        kwargs["is_set"] = is_set

    return retrieve_menu_fn(**kwargs)


# -----------------------------
# Jaccard + fusion
# -----------------------------

def _char_ngram(s: str, n: int = 2) -> set:
    if not s or len(s) < n:
        return set()
    return {s[i : i + n] for i in range(len(s) - n + 1)}


def _jaccard(a: str, b: str, n: int = 2) -> float:
    A = _char_ngram(a, n)
    B = _char_ngram(b, n)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def _patch_candidate_schema(candidates: List[Dict[str, Any]]) -> None:
    """
    retrieve_menu_fn이 반환하는 후보 dict 스키마가 단순할 수 있어,
    Step04의 Jaccard 필터가 동작하도록 최소 필드를 즉석에서 보강합니다.
    (기본 동작/설정은 변경하지 않음)
    """
    for c in candidates:
        if c.get("menu_variants_jaccard"):
            continue

        cand_menu = (
            c.get("menu")
            or c.get("menu_ko")
            or c.get("menu_name")
            or c.get("name")
            or ""
        )
        cand_menu = str(cand_menu).strip()
        if cand_menu:
            c["menu_variants_jaccard"] = [cand_menu]


def _jaccard_filter_candidates(
    ocr_item: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    min_jaccard: float = 0.15,
) -> List[Dict[str, Any]]:
    ocr_j = ocr_item.get("menu_jaccard")
    if not ocr_j:
        return []

    filtered: List[Dict[str, Any]] = []
    for c in candidates:
        variants = c.get("menu_variants_jaccard") or []
        if not variants:
            continue

        j = max(_jaccard(ocr_j, v) for v in variants)
        if j >= min_jaccard:
            c["_jaccard"] = j
            filtered.append(c)

    return filtered


def _fuse_score(c: Dict[str, Any]) -> float:
    return (
        0.6 * float(c.get("embed_score", c.get("score", 0.0)) or 0.0)
        + 0.3 * float(c.get("rerank_score", 0.0) or 0.0)
        + 0.1 * float(c.get("_jaccard", 0.0) or 0.0)
    )


# -----------------------------
# Normalize schema helpers
# -----------------------------

def _select_items_from_normalize(normalized: Any) -> Tuple[List[Dict[str, Any]], Dict[int, Dict[str, Any]]]:
    idx_map: Dict[int, Dict[str, Any]] = {}

    if isinstance(normalized, dict):
        norm_list = normalized.get("items_normalized")
        if isinstance(norm_list, list):
            for it in norm_list:
                if isinstance(it, dict) and "idx" in it:
                    try:
                        idx_map[int(it["idx"])] = it
                    except Exception:
                        continue

        if isinstance(normalized.get("items_merged"), list):
            return normalized["items_merged"], idx_map

        for k in ("items", "lines", "results"):
            if isinstance(normalized.get(k), list):
                return normalized[k], idx_map

        raise ValueError(
            "normalize json schema not supported (expected items_merged/items/lines/results). "
            f"available keys={list(normalized.keys())}"
        )

    if isinstance(normalized, list):
        return normalized, idx_map

    raise ValueError("normalize json must be list or dict")


def _merge_signals_from_item(
    item: Dict[str, Any],
    idx_map: Dict[int, Dict[str, Any]],
) -> Tuple[List[str], List[str], Optional[bool], str]:
    """items_merged 한 개를 입력으로 받아 Step04 RAG에 필요한 signals를 구성합니다."""
    text = str(item.get("text") or "")

    variants: List[str] = []
    detail_parts: List[str] = []
    is_set: Optional[bool] = item.get("is_set") if isinstance(item.get("is_set"), bool) else None

    for key in ("menu_variants_norm", "menu_name_variants_norm"):
        v = item.get(key)
        if isinstance(v, list) and v:
            variants = [str(x) for x in v if str(x).strip()]
            break

    d = item.get("detail_parts_norm")
    if isinstance(d, list):
        detail_parts = [str(x) for x in d if str(x).strip()]

    members = _safe_list(item.get("members"))
    if members and idx_map:
        vset: List[str] = []
        dset: List[str] = []
        any_set_seen = False
        any_set_true = False

        for mid in members:
            try:
                src = idx_map.get(int(mid))
            except Exception:
                src = None
            if not src:
                continue

            vv = src.get("menu_name_variants_norm")
            if isinstance(vv, list):
                for x in vv:
                    xs = str(x).strip()
                    if xs:
                        vset.append(xs)

            dd = src.get("detail_parts_norm")
            if isinstance(dd, list):
                for x in dd:
                    xs = str(x).strip()
                    if xs:
                        dset.append(xs)

            sv = src.get("is_set")
            if isinstance(sv, bool):
                any_set_seen = True
                if sv:
                    any_set_true = True

        if not variants and vset:
            variants = vset
        elif vset:
            variants = variants + vset

        if dset:
            detail_parts = detail_parts + dset

        if is_set is None and any_set_seen:
            is_set = any_set_true

    if not variants and text.strip():
        variants = [text.strip()]

    variants = _expand_slash_variants(variants)

    # detail parts unique
    seen = set()
    uniq_details: List[str] = []
    for x in detail_parts:
        xs = _norm_space(str(x))
        if not xs:
            continue
        if xs not in seen:
            uniq_details.append(xs)
            seen.add(xs)
    detail_parts = uniq_details

    if is_set is None:
        is_set = _infer_is_set_from_text(" ".join(variants) or text)

    return variants, detail_parts, is_set, text


# -----------------------------
# Step04 Main
# -----------------------------

def run_step_04_rag_match(
    run_dir: Path,
    top_k: int = 20,
    rerank_top_k: int = 5,
    score_threshold: float = 0.85,
    ambiguous_gap: float = 0.03,
    use_rerank: bool = True,
    include_debug: bool = False,
) -> Path:
    """
    Step04 실행.
    - normalize 결과를 읽어 각 항목별 RAG 매칭(+jaccard filter + rerank + fusion)을 수행하고 저장합니다.
    - output: <run_dir>/rag_match/rag_match.json
    """
    normalize_path = run_dir / "normalize" / "normalize.json"
    if not normalize_path.exists():
        alt = run_dir / "normalize" / "normalized.json"
        if alt.exists():
            normalize_path = alt
        else:
            raise FileNotFoundError(f"normalize output not found: {normalize_path}")

    normalized = _read_json(normalize_path)
    merged_items, idx_map = _select_items_from_normalize(normalized)

    out_items: List[Dict[str, Any]] = []
    stats = {"CONFIRMED": 0, "AMBIGUOUS": 0, "NOT_FOUND": 0, "TOTAL": 0}

    for item_i, item in enumerate(merged_items):
        if not isinstance(item, dict):
            continue

        # --- menu_candidate gate (minimal) ---
        if item.get("menu_candidate") is False:
            result = {
                "status": "NOT_FOUND",
                "best_match": None,
                "candidates": [],
                "used_query": None,
                "reason": "filtered_non_menu_candidate",
                "debug": {"index": item_i} if include_debug else None,
            }
        else:
            variants, detail_parts_norm, is_set, text = _merge_signals_from_item(item, idx_map)

            if not variants:
                result = {
                    "status": "NOT_FOUND",
                    "best_match": None,
                    "candidates": [],
                    "used_query": None,
                    "debug": {"reason": "empty_variants", "index": item_i} if include_debug else None,
                }
            else:
                result = _call_retrieve_menu(
                    variants=variants,
                    top_k=top_k,
                    score_threshold=score_threshold,
                    ambiguous_gap=ambiguous_gap,
                    include_debug=include_debug,
                    use_rerank=use_rerank,
                    rerank_top_k=rerank_top_k,
                    detail_parts_norm=detail_parts_norm,
                    is_set=is_set,
                )

                candidates = result.get("candidates") or []
                if not isinstance(candidates, list):
                    candidates = []

                # 1) candidate schema patch (so jaccard filter can run)
                _patch_candidate_schema(candidates)

                # 2) jaccard filter
                before_j = len(candidates)
                candidates = _jaccard_filter_candidates(item, candidates)
                after_j = len(candidates)

                if not candidates:
                    result["status"] = "NOT_FOUND"
                    result["best_match"] = None
                    result["candidates"] = []
                    if include_debug:
                        result["debug"] = result.get("debug") or {}
                        result["debug"].update(
                            {
                                "candidates_before_jaccard": before_j,
                                "candidates_after_jaccard": after_j,
                                "reason": "jaccard_filtered_all" if before_j > 0 else "no_candidates_from_retrieval",
                            }
                        )
                else:
                    # 3) rerank (forced)
                    if use_rerank:
                        cfg = RerankConfig(keep_debug=include_debug)
                        candidates = rerank_candidates(
                            candidates=candidates,
                            menu_name_variants_norm=variants,
                            detail_parts_norm=detail_parts_norm,
                            is_set=is_set,
                            config=cfg,
                            top_k=rerank_top_k,
                        )

                    # 4) score fusion + sort
                    for c in candidates:
                        c["final_score"] = _fuse_score(c)

                    candidates.sort(key=lambda x: x.get("final_score", 0.0), reverse=True)
                    result["candidates"] = candidates
                    result["best_match"] = candidates[0] if candidates else None
                    result["status"] = "CONFIRMED" if (result["best_match"] and result["best_match"].get("final_score", 0.0) >= 0.75) else "AMBIGUOUS"
                    if include_debug:
                        result["debug"] = result.get("debug") or {}
                        result["debug"].update(
                            {
                                "candidates_before_jaccard": before_j,
                                "candidates_after_jaccard": after_j,
                            }
                        )

        merged = dict(item)
        rag_out = {
            "status": result.get("status"),
            "used_query": result.get("used_query"),
            "best_match": result.get("best_match"),
            "candidates": result.get("candidates"),
            "debug": result.get("debug"),
        }
        if "reason" in result:
            rag_out["reason"] = result.get("reason")

        merged["rag_match"] = rag_out
        out_items.append(merged)

        stats["TOTAL"] += 1
        s = rag_out.get("status") or "NOT_FOUND"
        if s in stats:
            stats[s] += 1
        else:
            stats["NOT_FOUND"] += 1

    out_path = run_dir / "rag_match" / "rag_match.json"
    payload = {
        "run_dir": str(run_dir),
        "input_normalize": str(normalize_path),
        "stats": stats,
        "items": out_items,
    }
    _write_json(out_path, payload)
    return out_path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Step04 RAG match (schema aware, with jaccard + optional rerank)")
    p.add_argument("--run_id", type=str, required=False, help="Run id under <data_dir>/runs/<run_id>/")
    p.add_argument("--data_dir", type=str, default=None, help="Base data dir (default: <repo_root>/data).")
    p.add_argument("--run_dir", type=str, default=None, help="Direct run dir path (overrides --run_id).")

    p.add_argument("--top_k", type=int, default=20, help="Chroma retrieval candidates per query (recommend: 20~30)")
    p.add_argument("--rerank_top_k", type=int, default=5, help="Final candidates after rerank (recommend: 5)")
    p.add_argument("--score_threshold", type=float, default=0.85)
    p.add_argument("--ambiguous_gap", type=float, default=0.03)
    p.add_argument("--use_rerank", action="store_true", help="Enable rerank (recommended)")
    p.add_argument("--no_rerank", action="store_true", help="Disable rerank")
    p.add_argument("--include_debug", action="store_true", help="Include debug info in output")
    return p


def main():
    args = build_parser().parse_args()

    repo_root = Path(__file__).resolve().parents[4]  # menu_assistant/
    default_data_dir = repo_root / "data"
    data_dir = Path(args.data_dir) if args.data_dir else default_data_dir

    if args.run_dir:
        run_dir = Path(args.run_dir)
    else:
        if not args.run_id:
            raise ValueError("Either --run_dir or --run_id must be provided.")
        run_dir = _resolve_run_dir(data_dir, args.run_id)

    use_rerank = True
    if args.no_rerank:
        use_rerank = False
    if args.use_rerank:
        use_rerank = True

    out_path = run_step_04_rag_match(
        run_dir=run_dir,
        top_k=args.top_k,
        rerank_top_k=args.rerank_top_k,
        score_threshold=args.score_threshold,
        ambiguous_gap=args.ambiguous_gap,
        use_rerank=use_rerank,
        include_debug=args.include_debug,
    )

    print(f"[Step04] wrote: {out_path}")


if __name__ == "__main__":
    main()
