# AI/build_lexical_index.py
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True, help="data/menu_catalog.jsonl")
    ap.add_argument("--out", required=True, help="index/lexical/menus_norm.json")
    args = ap.parse_args()

    catalog = Path(args.catalog)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    ids: List[str] = []
    menus_norm: List[str] = []
    menus_raw: List[str] = []
    cats: List[str] = []

    with catalog.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj: Dict[str, Any] = json.loads(line)
            ids.append(obj["id"])
            menus_norm.append(obj.get("menu_norm", "") or "")
            menus_raw.append(obj.get("menu", "") or "")
            cats.append(obj.get("category_lv1", "OTHER") or "OTHER")

    payload = {
        "ids": ids,
        "menus_norm": menus_norm,
        "menus_raw": menus_raw,
        "category_lv1": cats,
        "count": len(ids),
    }
    out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] wrote: {out} (count={len(ids)})")

if __name__ == "__main__":
    main()
