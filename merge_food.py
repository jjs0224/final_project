from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

def _as_list(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    # 문자열/기타 타입이 들어오면 단일 원소 리스트로 취급
    s = str(v).strip()
    return [s] if s else []

def merge_food_data(food_data_dir: str, out_dir: str) -> None:
    food_dir = Path(food_data_dir)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []

    json_files = sorted(food_dir.rglob("*.json"))
    if not json_files:
        raise FileNotFoundError(f"No .json files found under: {food_dir}")

    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[SKIP] Failed to read {jf}: {e}")
            continue

        annotations = data.get("annotations", [])
        if not isinstance(annotations, list):
            continue

        for ann in annotations:
            if not isinstance(ann, dict):
                continue

            mi = ann.get("menu_information", {})
            if not isinstance(mi, dict):
                continue

            ko = (mi.get("ko") or "").strip()
            ing_ko = _as_list(mi.get("ingredients.ko"))
            ing_en = _as_list(mi.get("ingredients.en"))
            allergy = _as_list(mi.get("allergy"))

            # 원하는 필드가 전부 비어있으면 스킵 (원하면 제거 가능)
            if not (ko or ing_ko or ing_en or allergy):
                continue

            rows.append({
                "ko": ko,
                "ingredients_ko": ", ".join(ing_ko),
                "ingredients_en": ", ".join(ing_en),
                "allergy": ", ".join(allergy),
            })

    # CSV 저장 (엑셀에서 바로 열림)
    csv_file = out_path / "food_data_merged.csv"
    try:
        import csv
        with csv_file.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[ "ko", "ingredients_ko", "ingredients_en", "allergy"],
            )
            writer.writeheader()
            writer.writerows(rows)
    except Exception as e:
        raise RuntimeError(f"Failed to write CSV: {e}")

    # JSONL 저장 (한 줄 = 한 아이템)
    jsonl_file = out_path / "food_data_merged.jsonl"
    with jsonl_file.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Done. items={len(rows)}")
    print(f"- CSV : {csv_file}")
    print(f"- JSONL: {jsonl_file}")

if __name__ == "__main__":
    # 예시 경로: 프로젝트 구조에 맞게 수정하세요.
    # 스크린샷 기준: final_project/open_data/Training/food_data
    merge_food_data(
        food_data_dir=r"open_data/Training/food_data",
        out_dir=r"open_data/Training/_merged",
    )
    merge_food_data(
        food_data_dir=r"open_data/Validation/food_data",
        out_dir=r"open_data/Training/_merged",
    )