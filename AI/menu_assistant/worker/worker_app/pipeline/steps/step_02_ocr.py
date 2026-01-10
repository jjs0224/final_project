from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Step 02 - OCR on rectified image (PaddleOCR)")
    parser.add_argument("--run_id", required=True)
    parser.add_argument("--data_dir", default="data/runs")
    args = parser.parse_args()

    base = Path(args.data_dir) / args.run_id
    rectified_path = base / "rectify" / "rectified.jpg"
    ocr_dir = base / "ocr"
    ocr_dir.mkdir(parents=True, exist_ok=True)

    if not rectified_path.exists():
        raise FileNotFoundError(f"Rectified image not found: {rectified_path}")

    # TODO: connect your PaddleOCR det/rec here.
    # Suggested outputs:
    #  - ocr_raw.json (paddle raw)
    #  - ocr_norm.json (post-processed)
    #
    # For now we just emit a placeholder to confirm pipeline pathing.

    placeholder = {
        "input_image": str(rectified_path),
        "note": "Connect PaddleOCR here. This step expects rectified.jpg as input.",
    }
    (ocr_dir / "ocr_raw.json").write_text(json.dumps(placeholder, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] placeholder written: {ocr_dir / 'ocr_raw.json'}")


if __name__ == "__main__":
    main()
