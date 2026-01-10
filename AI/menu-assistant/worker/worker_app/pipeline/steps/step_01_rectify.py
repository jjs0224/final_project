from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from worker_app.vision.rectify import (
    RectifyConfig,
    rectify_image,
    read_image_bgr,
    write_image_bgr,
)


def _default_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def main():
    parser = argparse.ArgumentParser(description="Step 01 - Rectify menu image (no text detection)")
    parser.add_argument("--input", required=True, help="Path to original image")
    parser.add_argument("--run_id", default=None, help="Run ID (default: timestamp)")
    parser.add_argument("--data_dir", default="data/runs", help="Base output dir")
    parser.add_argument("--backend", default="none", choices=["none", "doctr", "dewarpnet", "docunet"])
    parser.add_argument("--device", default="cpu", help="cpu|cuda (depends on backend impl)")
    parser.add_argument("--model_dir", default=None, help="Optional model directory for backend weights")

    # Simple photometric knobs (optional)
    parser.add_argument("--gamma", type=float, default=1.15)
    parser.add_argument("--clahe_clip", type=float, default=2.0)
    parser.add_argument("--shadow_strength", type=float, default=0.85)

    args = parser.parse_args()

    run_id = args.run_id or _default_run_id()
    base = Path(args.data_dir) / run_id
    input_dir = base / "input"
    rectify_dir = base / "rectify"

    input_dir.mkdir(parents=True, exist_ok=True)
    rectify_dir.mkdir(parents=True, exist_ok=True)

    # Copy original path reference only (you can physically copy the file if you want)
    # Here we just record it in meta; if you prefer: shutil.copy(args.input, input_dir/"original.jpg")
    original_path = Path(args.input)

    img = read_image_bgr(str(original_path))

    cfg = RectifyConfig(
        backend=args.backend,
        device=args.device,
        model_dir=args.model_dir,
    )
    cfg.enhance.gamma = float(args.gamma)
    cfg.enhance.clahe_clip_limit = float(args.clahe_clip)
    cfg.illumination.strength = float(args.shadow_strength)

    res = rectify_image(img, cfg)

    out_img_path = rectify_dir / "rectified.jpg"
    out_meta_path = rectify_dir / "rectify_meta.json"

    write_image_bgr(str(out_img_path), res.image)

    meta = {
        "run_id": run_id,
        "input_image": str(original_path),
        "rectified_image": str(out_img_path),
        **res.meta,
    }
    out_meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] rectified image: {out_img_path}")
    print(f"[OK] rectify meta   : {out_meta_path}")


if __name__ == "__main__":
    main()
