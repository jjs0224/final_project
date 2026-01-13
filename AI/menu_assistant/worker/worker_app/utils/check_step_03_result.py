import json
from pathlib import Path
from typing import Dict, Any, List, Optional


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def summary(data: Dict[str, Any]) -> None:
    items_norm = data.get("items_normalized", [])
    items_merged = data.get("items_merged", [])

    total = len(items_norm)

    # ✅ Step_03 개편 반영: "normalized"가 아니라 menu_name_norm 기준
    kept = sum(1 for x in items_norm if x.get("menu_name_norm"))
    dropped = total - kept

    print("\n=== STEP 03 SUMMARY ===")
    print(f"- total OCR items         : {total}")
    print(f"- menu_name_norm kept     : {kept}")
    print(f"- dropped                 : {dropped}")
    print(f"- merged menu candidates  : {len(items_merged)}")


def show_dropped(items: List[Dict[str, Any]], limit: int = 10) -> None:
    print("\n=== DROPPED ITEMS (sample) ===")
    cnt = 0
    for it in items:
        if "dropped_reason" in it:
            print(f"- idx={it.get('idx'):>3} | raw='{it.get('raw_text')}' | reason={it.get('dropped_reason')}")
            cnt += 1
            if cnt >= limit:
                break
    if cnt == 0:
        print("(none)")


def _match_keywords(texts: List[str], keywords: Optional[List[str]]) -> bool:
    if not keywords:
        return True
    joined = " ".join([t for t in texts if t])
    return any(k in joined for k in keywords)


def show_merged(items: List[Dict[str, Any]], keywords: Optional[List[str]] = None) -> None:
    """
    ✅ Step_03 개편 반영:
    - items_merged에는 text(대표), menu_variants_norm, detail_parts_norm 이 들어갈 수 있음
    """
    print("\n=== MERGED MENU CANDIDATES ===")
    cnt = 0
    for i, it in enumerate(items):
        text = it.get("text", "")
        members = it.get("members", [])
        variants = it.get("menu_variants_norm", []) or []
        details = it.get("detail_parts_norm", []) or []

        if not _match_keywords([text] + variants + details, keywords):
            continue

        print(
            f"- {i:>3} | text='{text}' | variants={variants} | details={details} | from items={members}"
        )
        cnt += 1

    if cnt == 0:
        print("(no matches)")


def show_menu_and_details(items: List[Dict[str, Any]], keywords: Optional[List[str]] = None) -> None:
    """
    Step_03 구조화 결과 확인용 (items_normalized)
    - menu_name_norm
    - menu_name_variants_norm  ✅ 추가
    - detail_parts_norm
    """
    print("\n=== STRUCTURED (items_normalized): menu_name_norm / variants / detail_parts_norm ===")

    cnt = 0
    for it in items:
        menu = it.get("menu_name_norm")
        variants = it.get("menu_name_variants_norm", []) or []
        details = it.get("detail_parts_norm", []) or []

        if not menu:
            continue

        if not _match_keywords([menu] + variants + details, keywords):
            continue

        print(
            f"- idx={it.get('idx'):>3} | menu='{menu}' | variants={variants} | details={details}"
        )
        cnt += 1

    if cnt == 0:
        print("(no matches)")


def main():
    import argparse

    p = argparse.ArgumentParser(description="Quick check for step_03_normalize output")
    p.add_argument("--json", required=True, help="step_03 normalize output json path")
    p.add_argument(
        "--keywords",
        nargs="*",
        default=None,
        help="optional keywords to filter outputs (e.g. 만두 세트 비빔냉면)",
    )
    p.add_argument(
        "--show-structured",
        action="store_true",
        help="show items_normalized structured fields (menu_name_norm / variants / details)",
    )
    p.add_argument(
        "--merged-only",
        action="store_true",
        help="print merged section only (skip dropped/structured)",
    )
    args = p.parse_args()

    data = load_json(Path(args.json))

    summary(data)

    if not args.merged_only:
        show_dropped(data.get("items_normalized", []))
        if args.show_structured:
            show_menu_and_details(
                data.get("items_normalized", []),
                keywords=args.keywords
            )

    show_merged(data.get("items_merged", []), keywords=args.keywords)


if __name__ == "__main__":
    main()


"""
Example:

python -m menu_assistant.worker.worker_app.utils.check_step_03_result ^
  --json menu_assistant\data\runs\20260113_121958\normalize\normalize.json ^
  --show-structured ^
  --keywords 물냉면 비빔냉면 세트
"""
