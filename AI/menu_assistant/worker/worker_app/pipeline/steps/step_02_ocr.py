from __future__ import annotations

import argparse
import inspect
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from menu_assistant.worker.worker_app.vision.rectify import read_image_bgr, write_image_bgr


# Optional preprocess (pixel-only, geometry-invariant)
try:
    from AI.preprocess_korean_menu import PreprocessConfig, preprocess_menu_image
except Exception:
    try:
        from preprocess_korean_menu import PreprocessConfig, preprocess_menu_image
    except Exception:
        PreprocessConfig = None  # type: ignore
        preprocess_menu_image = None  # type: ignore


# -----------------------------
# Path resolving (run folder)
# -----------------------------
def resolve_rectified_from_run(data_dir: Path, run_id: str) -> Path:
    """
    Step1 output convention:
      <data_dir>/<run_id>/rectify/rectified.jpg
    """
    p = data_dir / run_id / "rectify" / "rectified.jpg"
    if not p.exists():
        raise FileNotFoundError(f"Rectified image not found: {p}")
    return p


# -----------------------------
# PaddleOCR safe construction
# -----------------------------
def import_paddleocr():
    try:
        from paddleocr import PaddleOCR  # type: ignore
        return PaddleOCR
    except Exception as e:
        raise RuntimeError(
            "PaddleOCR is not installed.\n"
            "Install (CPU):\n"
            "  pip install -U pip\n"
            "  pip install paddlepaddle\n"
            "  pip install paddleocr\n"
            "  pip install opencv-python numpy\n"
        ) from e


def build_paddleocr(
    PaddleOCR_cls: Any,
    lang: str,
    det_limit_side_len: int,
    det_limit_type: str,
    use_doc_unwarping: bool,
    use_textline_orientation: bool,
    det_model_dir: Optional[str],
    rec_model_dir: Optional[str],
    cls_model_dir: Optional[str],
) -> Any:
    sig = inspect.signature(PaddleOCR_cls.__init__)
    supported = set(sig.parameters.keys())

    kwargs: Dict[str, Any] = {}

    if "lang" in supported:
        kwargs["lang"] = lang

    if "det_limit_side_len" in supported:
        kwargs["det_limit_side_len"] = int(det_limit_side_len)
    if "det_limit_type" in supported:
        kwargs["det_limit_type"] = str(det_limit_type)

    # --- IMPORTANT: explicitly disable features if supported ---
    if "use_doc_unwarping" in supported:
        kwargs["use_doc_unwarping"] = bool(use_doc_unwarping)  # default False in CLI

    # 핵심: user가 켜지 않으면 False를 명시해서 textline_ori 모델 로딩 자체를 막음
    if "use_textline_orientation" in supported:
        kwargs["use_textline_orientation"] = bool(use_textline_orientation)  # default False

    # optional model dirs
    if det_model_dir and "det_model_dir" in supported:
        kwargs["det_model_dir"] = det_model_dir
    if rec_model_dir and "rec_model_dir" in supported:
        kwargs["rec_model_dir"] = rec_model_dir
    if cls_model_dir and "cls_model_dir" in supported:
        kwargs["cls_model_dir"] = cls_model_dir

    return PaddleOCR_cls(**kwargs)



# -----------------------------
# OCR run + robust parsing
# -----------------------------
def ocr_predict_or_ocr(ocr: Any, image_path: Path, image_bgr: np.ndarray) -> Any:
    """
    안정성 우선:
      1) predict(str(path))  <-- 최신 pipeline에서 가장 안정적
      2) predict(ndarray BGR)
      3) ocr(str(path))
      4) ocr(ndarray BGR)
    (절대 RGB로 변환해서 넣지 않음)
    """
    raw = None

    if hasattr(ocr, "predict") and callable(getattr(ocr, "predict")):
        # 1) path
        try:
            raw = ocr.predict(str(image_path))
            return raw
        except Exception:
            raw = None

        # 2) ndarray (BGR 그대로)
        try:
            raw = ocr.predict(image_bgr)
            return raw
        except Exception:
            raw = None

    if hasattr(ocr, "ocr") and callable(getattr(ocr, "ocr")):
        # 3) path
        try:
            raw = ocr.ocr(str(image_path))
            return raw
        except Exception:
            raw = None

        # 4) ndarray (BGR 그대로)
        raw = ocr.ocr(image_bgr)

    return raw



def parse_paddleocr_raw(raw: Any) -> List[Dict[str, Any]]:
    """
    Normalize PaddleOCR outputs into:
      [{text, score, poly(4pts), bbox[x1,y1,x2,y2]}, ...]
    Supports:
      A) Your current PaddleX-style dict:
         {'rec_texts': [...], 'rec_scores': [...], 'rec_polys': [...]} inside list[dict]
      B) list[dict] item-wise: {'text':..., 'points':..., 'score':...}
      C) classic: [poly, (text, score)]
      D) dict wrapper with list under res/result/results/data/lines
    """
    items: List[Dict[str, Any]] = []

    def add_item(text: str, score: float, poly_pts) -> None:
        # poly_pts can be numpy array (4,2) or list-like
        pts = poly_pts
        if hasattr(pts, "tolist"):
            pts = pts.tolist()
        pts_i = [[int(p[0]), int(p[1])] for p in pts]
        xs = [p[0] for p in pts_i]
        ys = [p[1] for p in pts_i]
        bbox = [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]
        items.append({"text": str(text), "score": float(score), "poly": pts_i, "bbox": bbox})

    if raw is None:
        return items

    # dict wrapper
    if isinstance(raw, dict):
        for k in ("results", "res", "result", "data", "lines"):
            v = raw.get(k)
            if isinstance(v, list):
                return parse_paddleocr_raw(v)
        return items

    # list wrapper
    if isinstance(raw, list):
        # unwrap page wrapper
        if len(raw) == 1 and isinstance(raw[0], list):
            raw = raw[0]

        # ---- Case A: list[dict] but dict contains batched lists (YOUR FORMAT) ----
        if len(raw) > 0 and isinstance(raw[0], dict):
            for d in raw:
                # 1) YOUR KEYS: rec_texts/rec_scores/rec_polys
                rec_texts = d.get("rec_texts")
                rec_scores = d.get("rec_scores")
                rec_polys = d.get("rec_polys") or d.get("dt_polys")

                if isinstance(rec_texts, list) and isinstance(rec_scores, list) and isinstance(rec_polys, list):
                    n = min(len(rec_texts), len(rec_scores), len(rec_polys))
                    for i in range(n):
                        add_item(rec_texts[i], float(rec_scores[i]), rec_polys[i])
                    # continue to next dict
                    continue

                # 2) item-wise dict format
                txt = d.get("text") or d.get("rec_text") or d.get("transcription")
                sc = d.get("confidence") or d.get("score") or d.get("rec_score") or 1.0
                pts = d.get("points") or d.get("poly") or d.get("bbox")
                if txt is not None and pts is not None:
                    # pts might be [ [x,y]... ] or np array
                    if hasattr(pts, "tolist"):
                        pts = pts.tolist()
                    if isinstance(pts, list) and len(pts) == 4:
                        add_item(str(txt), float(sc), pts)

            return items

        # ---- Case C: classic [poly, (text, score)] ----
        for entry in raw:
            try:
                if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                    continue
                poly, rec = entry
                if hasattr(poly, "tolist"):
                    poly = poly.tolist()
                if not (isinstance(poly, (list, tuple)) and len(poly) == 4):
                    continue

                if isinstance(rec, (list, tuple)) and len(rec) >= 2:
                    txt, sc = rec[0], float(rec[1])
                elif isinstance(rec, dict):
                    txt = rec.get("text") or rec.get("rec_text")
                    sc = float(rec.get("score", 1.0))
                else:
                    continue

                add_item(str(txt), float(sc), poly)
            except Exception:
                continue

    return items




def draw_vis(image_bgr: np.ndarray, items: List[Dict[str, Any]]) -> np.ndarray:
    vis = image_bgr.copy()
    for it in items:
        poly = it.get("poly")
        if not poly or len(poly) != 4:
            continue
        pts = np.array(poly, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(vis, [pts], True, (0, 255, 0), 2)
    return vis


# -----------------------------
# main
# -----------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Step 02 - PaddleOCR (use rectified image as source; output text+coords only)"
    )

    # Choose ONE: run_id (recommended) OR direct image path
    parser.add_argument("--run_id", default=None, help="Run id from Step1 (reads <data_dir>/<run_id>/rectify/rectified.jpg)")
    parser.add_argument("--data_dir", default="menu_assistant/data/runs", help="Runs base directory")
    parser.add_argument("--image", default=None, help="Direct path to rectified image (if not using --run_id)")

    # Output
    parser.add_argument("--out", default=None, help="Output json path. Default: <run>/ocr/ocr.json")
    parser.add_argument("--vis", default=None, help="Optional vis image path. Default: <run>/ocr/ocr_vis.jpg")
    parser.add_argument("--dump_raw", action="store_true", help="Save raw preview for debugging")

    # OCR params
    parser.add_argument("--lang", default="korean")
    parser.add_argument("--det_limit_side_len", type=int, default=4000)
    parser.add_argument("--det_limit_type", default="max")

    # Keep "auto correction" OFF by default
    parser.add_argument("--use_doc_unwarping", action="store_true", help="(Optional) enable doc unwarping if supported")
    parser.add_argument("--use_textline_orientation", action="store_true", help="(Optional) enable textline orientation if supported")

    # Custom model dirs (optional)
    parser.add_argument("--det_model_dir", default=None)
    parser.add_argument("--rec_model_dir", default=None)
    parser.add_argument("--cls_model_dir", default=None)

    # Optional preprocess (pixel-only)
    parser.add_argument("--use_preprocess", action="store_true", help="Apply preprocess_korean_menu (pixel-only)")
    parser.add_argument("--preprocess_mode", default="clahe_denoise_sharp")

    args = parser.parse_args()

    data_dir = Path(args.data_dir)

    # Resolve input image
    if args.image:
        img_path = Path(args.image)
        if not img_path.exists():
            raise FileNotFoundError(f"--image not found: {img_path}")
        run_base = None
    else:
        if not args.run_id:
            raise RuntimeError("Provide either --run_id or --image.")
        img_path = resolve_rectified_from_run(data_dir=data_dir, run_id=args.run_id)
        run_base = data_dir / args.run_id

    # Output paths
    if args.out:
        out_json = Path(args.out)
    else:
        if run_base is None:
            out_json = Path.cwd() / "ocr.json"
        else:
            out_json = run_base / "ocr" / "ocr.json"

    if args.vis:
        out_vis = Path(args.vis)
    else:
        out_vis = None if run_base is None else (run_base / "ocr" / "ocr_vis.jpg")

    out_json.parent.mkdir(parents=True, exist_ok=True)
    if out_vis is not None:
        out_vis.parent.mkdir(parents=True, exist_ok=True)

    # Load image
    img_bgr = read_image_bgr(str(img_path))

    # Optional preprocess (pixel-only)
    preprocess_meta: Dict[str, Any] = {"preprocess": {"enabled": False}}
    if args.use_preprocess:
        if PreprocessConfig is None or preprocess_menu_image is None:
            raise ImportError(
                "preprocess_korean_menu.py import failed. Check module path: AI/preprocess_korean_menu.py"
            )
        cfg = PreprocessConfig(mode=args.preprocess_mode, output="bgr")
        img_bgr = preprocess_menu_image(img_bgr, cfg)
        preprocess_meta = {
            "preprocess": {
                "enabled": True,
                "mode": args.preprocess_mode,
                "method": "geometry_invariant_pixel_only",
            }
        }

    # Build OCR
    PaddleOCR = import_paddleocr()
    ocr = build_paddleocr(
        PaddleOCR_cls=PaddleOCR,
        lang=args.lang,
        det_limit_side_len=args.det_limit_side_len,
        det_limit_type=args.det_limit_type,
        use_doc_unwarping=bool(args.use_doc_unwarping),
        use_textline_orientation=bool(args.use_textline_orientation),
        det_model_dir=args.det_model_dir,
        rec_model_dir=args.rec_model_dir,
        cls_model_dir=args.cls_model_dir,
    )

    # Run OCR
    t0 = time.time()
    raw = ocr_predict_or_ocr(ocr, img_path, img_bgr)
    items = parse_paddleocr_raw(raw)
    elapsed_ms = int((time.time() - t0) * 1000)

    # Save JSON: text + coords only
    result: Dict[str, Any] = {
        "image": str(img_path),
        "image_shape": [int(img_bgr.shape[0]), int(img_bgr.shape[1])],
        "engine": "paddleocr",
        "elapsed_ms": elapsed_ms,
        "paddleocr_config": {
            "lang": args.lang,
            "det_limit_side_len": int(args.det_limit_side_len),
            "det_limit_type": str(args.det_limit_type),
            "use_doc_unwarping": bool(args.use_doc_unwarping),
            "use_textline_orientation": bool(args.use_textline_orientation),
            "det_model_dir": args.det_model_dir,
            "rec_model_dir": args.rec_model_dir,
            "cls_model_dir": args.cls_model_dir,
        },
        "items": items,
        "notes": "Rectified image is treated as source. Step1 json/meta is not used. Script does not pass cls/angle correction kwargs.",
    }
    result.update(preprocess_meta)

    if args.dump_raw:
        try:
            result["_raw_type"] = type(raw).__name__
            result["_raw_preview"] = repr(raw)[:5000]
        except Exception:
            result["_raw_preview"] = "<raw_preview_failed>"

    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # Optional visualization
    if out_vis is not None:
        vis = draw_vis(img_bgr, items)
        write_image_bgr(str(out_vis), vis)

    print(f"[OK] items={len(items)} elapsed_ms={elapsed_ms}")
    print(f"[OK] json={out_json}")
    if out_vis is not None:
        print(f"[OK] vis={out_vis}")


if __name__ == "__main__":
    main()
