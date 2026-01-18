from __future__ import annotations

"""menu_assistant.worker.worker_app.pipeline.steps.step_04_rag_match

Step04는 "실행(입출력/스키마 정리)"만 담당합니다.

- 입력: <data_dir>/runs/<run_id>/normalize/normalize.json
- 출력: <run_dir>/rag_match/rag_match.json

실제 RAG 매칭 로직(Chroma 검색 + exact-match + 점수 융합 + 상태판정)은
menu_assistant.worker.worker_app.rag.retrieval 로 통합되어 있습니다.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from menu_assistant.worker.worker_app.rag.retrieval import match_menu_item


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _resolve_run_dir(data_dir: Path, run_id: str) -> Path:
    return data_dir / "runs" / run_id


def _safe_list(v: Any) -> List[Any]:
    return v if isinstance(v, list) else []


def _select_items_from_normalize(normalized: Any) -> Tuple[List[Dict[str, Any]], Dict[int, Dict[str, Any]]]:
    """normalize.json 스키마 호환: items_merged + items_normalized(idx_map) 우선."""
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
        raise ValueError(f"normalize json schema not supported. keys={list(normalized.keys())}")
    if isinstance(normalized, list):
        return normalized, idx_map
    raise ValueError("normalize json must be list or dict")


def _merge_signals_from_item(item: Dict[str, Any], idx_map: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    """Step04가 retrieval에 넘길 신호(variants/menu_jaccard/detail_parts/is_set)를 구성."""
    text = str(item.get("text") or "")
    menu_jaccard = str(item.get("menu_jaccard") or "")

    variants: List[str] = []
    for key in ("menu_name_variants_norm", "menu_variants_norm"):
        v = item.get(key)
        if isinstance(v, list) and v:
            variants = [str(x).strip() for x in v if str(x).strip()]
            break
    if not variants and text.strip():
        variants = [text.strip()]

    detail_parts: List[str] = []
    d = item.get("detail_parts_norm")
    if isinstance(d, list):
        detail_parts = [str(x).strip() for x in d if str(x).strip()]

    is_set = item.get("is_set") if isinstance(item.get("is_set"), bool) else None

    members = _safe_list(item.get("members"))
    if members and idx_map:
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
                        variants.append(xs)
            dd = src.get("detail_parts_norm")
            if isinstance(dd, list):
                for x in dd:
                    xs = str(x).strip()
                    if xs:
                        detail_parts.append(xs)
            sv = src.get("is_set")
            if is_set is None and isinstance(sv, bool):
                is_set = sv

    # dedup (order-preserving)
    seen = set()
    uniq_variants: List[str] = []
    for x in variants:
        if x and x not in seen:
            uniq_variants.append(x)
            seen.add(x)
    variants = uniq_variants

    seen = set()
    uniq_detail: List[str] = []
    for x in detail_parts:
        if x and x not in seen:
            uniq_detail.append(x)
            seen.add(x)
    detail_parts = uniq_detail

    return {
        "text": text,
        "variants": variants,
        "menu_jaccard": menu_jaccard,
        "detail_parts_norm": detail_parts,
        "is_set": is_set,
    }


def run_step_04_rag_match(
    run_dir: Path,
    top_k: int = 20,
    rerank_top_k: int = 5,
    score_threshold: float = 0.55,
    ambiguous_gap: float = 0.03,
    use_rerank: bool = True,
    include_debug: bool = False,
) -> Path:
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

    for item in merged_items:
        if not isinstance(item, dict):
            continue

        if item.get("menu_candidate") is False:
            rag = {
                "status": "NOT_FOUND",
                "used_query": None,
                "best_match": None,
                "candidates": [],
                "debug": {"reason": "filtered_non_menu_candidate"} if include_debug else None,
            }
        else:
            sig = _merge_signals_from_item(item, idx_map)
            rag = match_menu_item(
                variants=sig["variants"],
                menu_jaccard=sig.get("menu_jaccard") or "",
                detail_parts_norm=sig.get("detail_parts_norm") or [],
                is_set=sig.get("is_set"),
                top_k=top_k,
                rerank_top_k=rerank_top_k,
                score_threshold=score_threshold,
                ambiguous_gap=ambiguous_gap,
                use_rerank=use_rerank,
                include_debug=include_debug,
            )

        merged = dict(item)
        merged["rag_match"] = rag
        out_items.append(merged)

        stats["TOTAL"] += 1
        s = rag.get("status") or "NOT_FOUND"
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
    p = argparse.ArgumentParser(description="Step04 RAG match (runner only)")
    p.add_argument("--run_id", type=str, required=False)
    p.add_argument("--data_dir", type=str, default=None)
    p.add_argument("--run_dir", type=str, default=None)
    p.add_argument("--top_k", type=int, default=20)
    p.add_argument("--rerank_top_k", type=int, default=5)
    p.add_argument("--score_threshold", type=float, default=0.55)
    p.add_argument("--ambiguous_gap", type=float, default=0.03)
    p.add_argument("--use_rerank", action="store_true")
    p.add_argument("--no_rerank", action="store_true")
    p.add_argument("--include_debug", action="store_true")
    return p


def main() -> None:
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
