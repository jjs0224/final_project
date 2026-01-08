# AI/build_menu_catalog.py
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from AI.data.category_rules import normalize_menu, predict_category

def make_text_for_embed(menu: str, ingredients_ko: List[str], alg_tags: List[str], max_ing: int = 8) -> str:
    ings = (ingredients_ko or [])[:max_ing]
    alg = alg_tags or []
    # 임베딩 입력은 "menu 중심" + "핵심 재료" + "알러지 태그"
    return f"메뉴명: {menu} | 재료: {', '.join(ings)} | 알러지: {', '.join(alg)}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="data/menu_final_with_allergen.json")
    ap.add_argument("--out", required=True, help="data/menu_catalog.jsonl")
    ap.add_argument("--max_ing", type=int, default=8)
    args = ap.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    data = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("src json must be a list of objects")

    with out.open("w", encoding="utf-8") as f:
        for i, row in enumerate(data):
            menu = (row.get("menu") or "").strip()
            ingredients_ko = row.get("ingredients_ko") or []
            alg = row.get("ALG_TAG") or []

            if not isinstance(ingredients_ko, list):
                ingredients_ko = [str(ingredients_ko)]
            if not isinstance(alg, list):
                alg = [str(alg)]

            cat = predict_category(menu)

            doc: Dict[str, Any] = {
                "id": f"menu_{i:08d}",
                "menu": menu,
                "menu_norm": normalize_menu(menu),
                "ingredients_ko": ingredients_ko,
                "ALG_TAG": alg,
                "category_lv1": cat.category_lv1,
                "category_conf": round(float(cat.confidence), 4),
                "category_matched": cat.matched,
                "text_for_embed": make_text_for_embed(menu, ingredients_ko, alg, max_ing=args.max_ing),
            }
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(f"[OK] wrote: {out} (count={len(data)})")

if __name__ == "__main__":
    main()
