"""
Step 04: RAG Match (Optimized)
- Input:  data/runs/<run_id>/normalize/normalize.json
- Output: data/runs/<run_id>/rag/rag_match.json

Optimization:
- If menu_name_norm is empty/null AND variants empty -> skip retrieval (major speed-up)
- Optional skip rules: too short, price/notice patterns, low OCR score
- Always writes rag_match block with status: CONFIRMED/AMBIGUOUS/NOT_FOUND/SKIPPED
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from menu_assistant.worker.worker_app.rag.retrieval import retrieve_menu


# ==============================
# SKIP RULES (tunable)
# ==============================
DEFAULT_MIN_MENU_LEN = 2          # 1글자 후보는 대부분 노이즈
DEFAULT_MIN_OCR_SCORE = 0.0       # 필요 시 0.5 등으로 올리세요

# 가격/안내문/상호명에 자주 등장하는 패턴(필요시 확장)
_PRICE_RE = re.compile(r"(\d[\d,]*\s*원)|(\d+\s*￦)|(\d+\s*KRW)", re.IGNORECASE)
_NOTICE_RE = re.compile(
    r"(주문|셀프|포장|배달|키오스크|원산지|영업|휴무|공지|안내|전화|예약|매장|테이블|카드|현금|VAT|부가세)",
    re.IGNORECASE,
)
_SHOP_RE = re.compile(r"(전문점|식당|카페|분식|매장|\d+호점|\d+점|\w+점)$")


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def ensure_list_of_items(normalized: Any) -> List[Dict[str, Any]]:
    """
    normalize.json 구조가 프로젝트마다 달라질 수 있으므로,
    재귀적으로 탐색해서 "list[dict]" (아이템 목록)을 찾아 반환한다.
    """

    def is_item_dict(d: Dict[str, Any]) -> bool:
        candidate_keys = (
            "menu_name_norm",
            "menu_name_variants_norm",
            "raw_text",
            "text",
            "bbox",
            "poly",
        )
        return any(k in d for k in candidate_keys)

    def find_list_of_dicts(obj: Any) -> Optional[List[Dict[str, Any]]]:
        if isinstance(obj, list):
            if obj and all(isinstance(x, dict) for x in obj):
                return obj  # type: ignore
            for x in obj:
                found = find_list_of_dicts(x)
                if found:
                    return found
            return None

        if isinstance(obj, dict):
            for key in (
                "items",
                "results",
                "data",
                "lines",
                "menus",
                "blocks",
                "rows",
                "pages",
                "records",
                "normalized",
            ):
                v = obj.get(key)
                if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
                    return v  # type: ignore

            if is_item_dict(obj):
                return [obj]  # type: ignore

            for v in obj.values():
                found = find_list_of_dicts(v)
                if found:
                    return found
            return None

        return None

    found = find_list_of_dicts(normalized)
    if found is None:
        top_type = type(normalized).__name__
        top_keys = list(normalized.keys()) if isinstance(normalized, dict) else None
        raise ValueError(
            f"Could not locate list[dict] items in normalize.json. top_type={top_type}, top_keys={top_keys}"
        )
    return found


def build_query_variants(item: Dict[str, Any]) -> List[str]:
    """
    Step3 normalize 결과에서 variants를 추출.
    - 우선순위: menu_name_variants_norm (list[str])
    - fallback: menu_name_norm (str)
    """
    variants = item.get("menu_name_variants_norm") or []
    if isinstance(variants, list):
        variants = [str(x).strip() for x in variants if str(x).strip()]
    else:
        variants = []

    if not variants:
        v = str(item.get("menu_name_norm", "")).strip()
        if v:
            variants = [v]

    return variants


def should_skip_rag(
    item: Dict[str, Any],
    variants: List[str],
    min_menu_len: int,
    min_ocr_score: float,
) -> Optional[str]:
    """
    RAG 스킵 사유를 문자열로 반환 (스킵하지 않으면 None).
    """

    menu_norm = str(item.get("menu_name_norm") or "").strip()
    raw_text = str(item.get("raw_text") or item.get("text") or "").strip()

    # 0) menu 후보 자체가 없음 (요청하신 핵심 최적화)
    if not menu_norm and not variants:
        return "empty_menu_name_norm_and_variants"

    # 1) 너무 짧은 메뉴 후보
    # (variants 중에 충분히 긴 것이 하나도 없으면 스킵)
    longest = max([len(v) for v in variants], default=len(menu_norm))
    if longest < min_menu_len:
        return f"too_short(<{min_menu_len})"

    # 2) OCR 점수 낮음 (필요할 때만 min_ocr_score를 올리면 됨)
    ocr_score = item.get("score")
    if isinstance(ocr_score, (int, float)) and ocr_score < min_ocr_score:
        return f"low_ocr_score(<{min_ocr_score})"

    # 3) 가격/안내문 패턴 (대개 메뉴가 아님)
    text_for_rule = raw_text or menu_norm
    if _PRICE_RE.search(text_for_rule):
        return "price_pattern"
    if _NOTICE_RE.search(text_for_rule):
        return "notice_pattern"

    # 4) 상호명/업장명 패턴(전문점/식당 등)
    # 주의: 진짜 메뉴명이 "전문점"으로 끝나진 않는 편이라 높은 스킵 효율
    if _SHOP_RE.search(text_for_rule):
        return "shop_name_pattern"

    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", required=True, help="runs 폴더 하위 run id (예: 20260113_121958)")
    parser.add_argument("--top_k", type=int, default=5, help="Chroma query top_k")
    parser.add_argument("--threshold", type=float, default=0.85, help="CONFIRMED/AMBIGUOUS 판정 score threshold")
    parser.add_argument("--ambiguous_gap", type=float, default=0.03, help="best-second gap < gap 이면 AMBIGUOUS")
    parser.add_argument("--save_candidates_k", type=int, default=3, help="저장할 후보 개수(파일 크기 관리)")
    parser.add_argument("--include_debug", action="store_true", help="retrieval debug 정보 저장")

    # ✅ 스킵 튜닝 옵션
    parser.add_argument("--min_menu_len", type=int, default=DEFAULT_MIN_MENU_LEN, help="RAG 수행 최소 글자수")
    parser.add_argument("--min_ocr_score", type=float, default=DEFAULT_MIN_OCR_SCORE, help="RAG 수행 최소 OCR score")

    args = parser.parse_args()

    # .../menu_assistant/worker/worker_app/pipeline/steps/step_04_rag_match.py
    # parents[4] -> menu_assistant/
    menu_assistant_dir = Path(__file__).resolve().parents[4]
    runs_dir = menu_assistant_dir / "data" / "runs"
    run_dir = runs_dir / args.run_id

    normalize_path = run_dir / "normalize" / "normalize.json"
    if not normalize_path.exists():
        raise FileNotFoundError(f"normalize.json not found: {normalize_path}")

    out_path = run_dir / "rag" / "rag_match.json"

    normalized_raw = load_json(normalize_path)
    items = ensure_list_of_items(normalized_raw)

    results: List[Dict[str, Any]] = []
    total = len(items)

    skipped = 0
    queried = 0

    for i, item in enumerate(items, start=1):
        variants = build_query_variants(item)

        reason = should_skip_rag(
            item=item,
            variants=variants,
            min_menu_len=int(args.min_menu_len),
            min_ocr_score=float(args.min_ocr_score),
        )

        # ✅ 스킵이면 retrieval 호출하지 않음
        if reason is not None:
            skipped += 1
            item_out = dict(item)
            item_out["rag_match"] = {
                "status": "SKIPPED",
                "reason": reason,
                "used_query": None,
                "best_match": None,
                "candidates": [],
                "debug": None,
            }
            results.append(item_out)

            if i % 50 == 0 or i == total:
                print(f"[INFO] processed {i}/{total} (queried={queried}, skipped={skipped})")
            continue

        # retrieval 수행
        queried += 1
        rag_res = retrieve_menu(
            variants=variants,
            top_k=args.top_k,
            score_threshold=args.threshold,
            ambiguous_gap=args.ambiguous_gap,
            include_debug=args.include_debug,
        )

        # 파일 크기 관리: candidates 상위 k만 저장
        if isinstance(rag_res.get("candidates"), list):
            rag_res["candidates"] = rag_res["candidates"][: max(0, int(args.save_candidates_k))]

        item_out = dict(item)
        item_out["rag_match"] = rag_res
        results.append(item_out)

        if i % 50 == 0 or i == total:
            print(f"[INFO] processed {i}/{total} (queried={queried}, skipped={skipped})")

    save_json(out_path, results)
    print("[OK] rag match saved")
    print(f" - input : {normalize_path}")
    print(f" - output: {out_path}")
    print(f" - queried: {queried}")
    print(f" - skipped: {skipped}")


if __name__ == "__main__":
    main()
