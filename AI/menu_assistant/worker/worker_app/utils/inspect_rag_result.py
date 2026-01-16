# inspect_rag_result.py
# RAG 결과 요약 출력 스크립트 (가독성 개선 버전)
# - rag_match.json 구조는 그대로 유지하고, 출력(뷰)만 보기 좋게 분리
#   1) CONFIRMED: 확정 매칭(기본 final_score/jaccard 기준 통과)
#   2) AMBIGUOUS: status는 CONFIRMED라도 신뢰가 낮아 "애매"로 분리
#   3) FILTERED: menu_candidate=false 또는 filtered_* reason
#   4) NOT_FOUND: 그 외 미매칭
#
# 실행:
#   python inspect_rag_result.py
# 또는:
#   python inspect_rag_result.py --run-id 20260115_200545
#   python inspect_rag_result.py --path <rag_match.json>

import json
import argparse
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _fmt(v):
    if v is None:
        return "-"
    try:
        return f"{float(v):.3f}"
    except Exception:
        return str(v)


def _join_and_clip(val, max_len: int = 60) -> str:
    """list/str/None을 받아 보기 좋은 문자열로 만들고 길면 자른다."""
    if val is None:
        s = ""
    elif isinstance(val, list):
        s = ", ".join(map(str, val))
    else:
        s = str(val)

    s = s.strip()
    if len(s) > max_len:
        s = s[:max_len] + "..."
    return s


def _extract_ing_tags(match: Dict[str, Any]) -> Tuple[str, str]:
    """match dict에서 ingredients_ko / alg_tags 계열을 방어적으로 추출."""
    ingredients = (
        match.get("ingredients_ko")
        or match.get("ingredients")
        or match.get("ingredient_ko")
        or []
    )
    alg_tags = (
        match.get("alg_tags")
        or match.get("ALG_TAG")
        or match.get("allergens")
        or []
    )
    return _join_and_clip(ingredients), _join_and_clip(alg_tags)


def _load_json(p: Path) -> Dict[str, Any]:
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def _is_filtered(item: Dict[str, Any]) -> Tuple[bool, str]:
    """필터(메뉴 아님 등) 여부와 이유."""
    if item.get("menu_candidate") is False:
        reason = (item.get("rag_match") or {}).get("reason") or "menu_candidate=false"
        return True, reason

    rag = item.get("rag_match") or {}
    reason = rag.get("reason")
    if isinstance(reason, str) and reason.startswith("filtered"):
        return True, reason

    return False, ""


def _classify(item: Dict[str, Any], final_th: float, jacc_th: float, margin_th: float) -> str:
    """출력용 그룹 분류: CONFIRMED / AMBIGUOUS / FILTERED / NOT_FOUND"""
    rag = item.get("rag_match") or {}
    status = rag.get("status") or "UNKNOWN"

    is_filt, _ = _is_filtered(item)
    if is_filt:
        return "FILTERED"

    if status != "CONFIRMED":
        return "NOT_FOUND"

    best = rag.get("best_match") or {}
    final_score = best.get("final_score")
    jacc = best.get("_jaccard")

    # 후보 점수 차이(Top1 - Top2)가 작으면 애매로 분류
    cands = rag.get("candidates") or []
    top1 = None
    top2 = None
    if isinstance(cands, list) and len(cands) >= 1:
        top1 = (cands[0] or {}).get("final_score")
    if isinstance(cands, list) and len(cands) >= 2:
        top2 = (cands[1] or {}).get("final_score")

    margin = None
    try:
        if top1 is not None and top2 is not None:
            margin = float(top1) - float(top2)
    except Exception:
        margin = None

    # 애매 조건: final 낮음 OR jaccard 낮음 OR margin 너무 작음
    try:
        if final_score is not None and float(final_score) < float(final_th):
            return "AMBIGUOUS"
    except Exception:
        pass

    try:
        if jacc is not None and float(jacc) < float(jacc_th):
            return "AMBIGUOUS"
    except Exception:
        pass

    try:
        if margin is not None and float(margin) < float(margin_th):
            return "AMBIGUOUS"
    except Exception:
        pass

    return "CONFIRMED"


def main():
    # ===== 실행 환경에 맞춘 기본 경로 설정 (고정 Windows 경로 제거) =====
    here = Path(__file__).resolve().parent

    # 1) 같은 폴더에 rag_match.json이 있으면 그걸 기본으로 사용
    default_rag_path = here / "rag_match.json"

    # 2) (선택) 사용자가 프로젝트 runs 구조에서 돌릴 때를 대비한 fallback 템플릿
    #    --run-id를 주면 runs/<run-id>/rag_match/rag_match.json을 자동으로 잡아줌
    DEFAULT_RUN_ID = "20260116_173543"
    BASE_RUNS_DIR = Path(r"C:\Users\201\Desktop\PGHfolder\Final_project\AI\menu_assistant\data\runs")

    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=DEFAULT_RUN_ID, help="runs 하위 타임스탬프 폴더명")
    ap.add_argument(
        "--path",
        default=str(default_rag_path),
        help="rag_match.json path (기본: 스크립트와 같은 폴더의 rag_match.json)",
    )
    ap.add_argument("--top-n", type=int, default=3, help="AMBIGUOUS 후보 출력 개수")

    # 애매 판정 기준(필요 시 조정)
    ap.add_argument("--final-th", type=float, default=0.85, help="final_score 미만이면 AMBIGUOUS")
    ap.add_argument("--jacc-th", type=float, default=0.30, help="_jaccard 미만이면 AMBIGUOUS")
    ap.add_argument("--margin-th", type=float, default=0.03, help="Top1-Top2 final_score 차이 미만이면 AMBIGUOUS")

    args = ap.parse_args()

    # --path를 안 줬고(=기본값 유지) 현재 폴더에 rag_match.json이 없으면 runs 구조로 fallback
    if args.path == str(default_rag_path) and not Path(args.path).exists():
        args.path = str(BASE_RUNS_DIR / args.run_id / "rag_match" / "rag_match.json")

    data = _load_json(Path(args.path))
    stats = data.get("stats") or {}
    items: List[Dict[str, Any]] = data.get("items") or data.get("results") or []

    # 그룹별 수집
    buckets: Dict[str, List[Dict[str, Any]]] = {
        "CONFIRMED": [],
        "AMBIGUOUS": [],
        "FILTERED": [],
        "NOT_FOUND": [],
    }

    for item in items:
        group = _classify(item, args.final_th, args.jacc_th, args.margin_th)
        buckets[group].append(item)

    # ========================
    # SUMMARY
    # ========================
    print("=" * 60)
    print("RAG MATCH SUMMARY (view-level grouping)")
    print("=" * 60)
    print(f"run_id      : {args.run_id}")
    print(f"rag_path    : {args.path}")
    if stats:
        # 원본 stats도 같이 보여주되, 사람이 보는 그룹 카운트도 함께 표시
        print(f"raw_stats   : {stats}")
    print(
        "group_count : "
        f"CONFIRMED={len(buckets['CONFIRMED'])}, "
        f"AMBIGUOUS={len(buckets['AMBIGUOUS'])}, "
        f"FILTERED={len(buckets['FILTERED'])}, "
        f"NOT_FOUND={len(buckets['NOT_FOUND'])}"
    )
    print(
        f"criteria    : final_th={args.final_th}, jacc_th={args.jacc_th}, margin_th={args.margin_th}"
    )
    print("=" * 60)

    # 출력 헬퍼
    def _get_text(item: Dict[str, Any]) -> str:
        return ((item.get("text") or item.get("query") or "").strip())

    def _get_rag(item: Dict[str, Any]) -> Dict[str, Any]:
        return item.get("rag_match") or {}

    # ========================
    # CONFIRMED
    # ========================
    print("\n[CONFIRMED]")
    if not buckets["CONFIRMED"]:
        print("- (none)")
    for item in buckets["CONFIRMED"]:
        rag = _get_rag(item)
        best = rag.get("best_match") or {}
        text = _get_text(item)

        menu = best.get("menu") or best.get("menu_ko") or best.get("menu_name") or "UNKNOWN"
        ing_s, tag_s = _extract_ing_tags(best)

        print(f"- {text} → {menu}")
        print(f"  · 재료: {ing_s if ing_s else '-'}")
        print(f"  · 알러지: {tag_s if tag_s else '-'}")
        print(
            f"  · score: final={_fmt(best.get('final_score'))} "
            f"(rerank={_fmt(best.get('rerank_score'))}, jaccard={_fmt(best.get('_jaccard'))})"
        )

    # ========================
    # AMBIGUOUS
    # ========================
    print("\n[AMBIGUOUS]")
    if not buckets["AMBIGUOUS"]:
        print("- (none)")
    for item in buckets["AMBIGUOUS"]:
        rag = _get_rag(item)
        text = _get_text(item)
        cands = rag.get("candidates") or []

        best = rag.get("best_match") or (cands[0] if cands else {}) or {}
        menu = best.get("menu") or best.get("menu_ko") or best.get("menu_name") or "UNKNOWN"

        print(f"- {text} → {menu} (Top-{min(args.top_n, len(cands))} candidates)")

        top_n = min(args.top_n, len(cands))
        for r, cand in enumerate(cands[:top_n], start=1):
            menu_c = cand.get("menu") or cand.get("menu_ko") or cand.get("menu_name") or "UNKNOWN"
            ing_s, tag_s = _extract_ing_tags(cand)

            print(
                f"  {r}) {menu_c} | "
                f"final={_fmt(cand.get('final_score'))} rerank={_fmt(cand.get('rerank_score'))} jacc={_fmt(cand.get('_jaccard'))}"
            )
            print(f"     - 재료: {ing_s if ing_s else '-'}")
            print(f"     - 알러지: {tag_s if tag_s else '-'}")

    # ========================
    # FILTERED
    # ========================
    print("\n[FILTERED / NOT MENU]")
    if not buckets["FILTERED"]:
        print("- (none)")
    for item in buckets["FILTERED"]:
        text = _get_text(item)
        is_filt, reason = _is_filtered(item)
        reason = reason or "filtered"
        print(f"- {text} (reason: {reason})")

    # ========================
    # NOT_FOUND
    # ========================
    print("\n[NOT_FOUND]")
    if not buckets["NOT_FOUND"]:
        print("- (none)")
    for item in buckets["NOT_FOUND"]:
        rag = _get_rag(item)
        text = _get_text(item)
        used_query = rag.get("used_query")
        if used_query:
            print(f"- {text} (used_query: {used_query})")
        else:
            print(f"- {text}")


if __name__ == "__main__":
    main()
