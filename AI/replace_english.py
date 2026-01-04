from __future__ import annotations

from pathlib import Path
import json
import re
import argparse
from typing import Any, Dict, List, Tuple, Optional

from PIL import Image, ImageDraw, ImageFont


# -------------------------
# 1) 한글만 추출
# -------------------------
def keep_korean_only(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip()
    s = re.sub(r"[^가-힣\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# -------------------------
# 2) 번역기(로컬 HF Marian)
# -------------------------
def build_translator():
    from transformers import pipeline
    return pipeline("translation", model="Helsinki-NLP/opus-mt-ko-en")

translator = build_translator()

def ko_to_en(text: str) -> str:
    if not text:
        return ""
    out = translator(text, max_length=128)
    return out[0]["translation_text"].strip()


# -------------------------
# 3) JSON 파싱
# -------------------------
def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))

def poly_to_bbox(poly: List[List[float]]) -> Tuple[int, int, int, int]:
    xs = [pt[0] for pt in poly]
    ys = [pt[1] for pt in poly]
    return int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))

def get_items(data: dict) -> List[dict]:
    texts = data.get("rec_texts", [])
    polys = data.get("rec_polys", None)
    boxes = data.get("rec_boxes", None)

    items = []
    for i in range(len(texts)):
        t = texts[i]
        poly = polys[i] if polys and i < len(polys) else None
        box = boxes[i] if boxes and i < len(boxes) else None

        if box and len(box) == 4:
            x1, y1, x2, y2 = map(float, box)
            bbox = (x1, y1, x2, y2)
        elif poly:
            bbox = tuple(map(float, poly_to_bbox(poly)))
        else:
            continue

        items.append({"text": t, "poly": poly, "bbox": bbox})
    return items


# -------------------------
# 4) 좌표가 "원본 좌표"인지 자동 판별 + 필요 시 스케일 역변환
# -------------------------
def det_scale_from_params(orig_w: int, orig_h: int, det_params: dict) -> float:
    limit_type = det_params.get("limit_type", "max")
    limit_side_len = float(det_params.get("limit_side_len", 0) or 0)

    if limit_side_len <= 0:
        return 1.0

    if limit_type == "max":
        long_side = max(orig_w, orig_h)
        return 1.0 if long_side <= limit_side_len else (limit_side_len / long_side)
    elif limit_type == "min":
        short_side = min(orig_w, orig_h)
        return 1.0 if short_side >= limit_side_len else (limit_side_len / short_side)
    return 1.0

def guess_coord_space(items: List[dict], orig_w: int, orig_h: int) -> str:
    """
    rec_boxes 최대값이 원본 크기와 비슷하면 'orig'
    아니면 'scaled'로 가정(리사이즈된 좌표)
    """
    if not items:
        return "orig"

    max_x2 = max(it["bbox"][2] for it in items)
    max_y2 = max(it["bbox"][3] for it in items)

    # 원본과의 근접도 판단(10% 여유)
    if max_x2 <= orig_w * 1.10 and max_y2 <= orig_h * 1.10:
        return "orig"
    return "scaled"

def map_box_scaled_to_orig(box: Tuple[float, float, float, float], s: float) -> Tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    if s == 0:
        s = 1.0
    return (int(round(x1 / s)), int(round(y1 / s)), int(round(x2 / s)), int(round(y2 / s)))

def map_poly_scaled_to_orig(poly: List[List[float]], s: float) -> List[Tuple[int, int]]:
    if s == 0:
        s = 1.0
    pts = []
    for p in poly:
        pts.append((int(round(p[0] / s)), int(round(p[1] / s))))
    return pts


# -------------------------
# 5) 자동 줄바꿈 + 폰트 맞춤
# -------------------------
def text_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> Tuple[int, int]:
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    return (r - l), (b - t)

def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_w: int) -> List[str]:
    words = text.split()
    if not words:
        return []
    lines = []
    cur = words[0]
    for w in words[1:]:
        trial = cur + " " + w
        w_trial, _ = text_bbox(draw, trial, font)
        if w_trial <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines

def fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box_w: int,
    box_h: int,
    font_path: str,
    max_size: int = 28,
    min_size: int = 10,
    pad: int = 4,
    gap: int = 2,
) -> Tuple[ImageFont.FreeTypeFont, List[str]]:
    target_w = max(1, box_w - 2 * pad)
    target_h = max(1, box_h - 2 * pad)

    for size in range(max_size, min_size - 1, -1):
        font = ImageFont.truetype(font_path, size)
        lines = wrap_text(draw, text, font, target_w)
        if not lines:
            continue
        max_line_w = max(text_bbox(draw, ln, font)[0] for ln in lines)
        line_h = text_bbox(draw, "Ag", font)[1]
        total_h = len(lines) * line_h + (len(lines) - 1) * gap
        if max_line_w <= target_w and total_h <= target_h:
            return font, lines

    font = ImageFont.truetype(font_path, min_size)
    lines = wrap_text(draw, text, font, max(1, box_w - 8))
    return font, lines


# -------------------------
# 6) 원본 이미지에 덮어쓰기
# -------------------------
def replace_on_original(
    original_image_path: Path,
    json_path: Path,
    out_path: Path,
    font_path: str,
):
    img = Image.open(original_image_path).convert("RGB")
    orig_w, orig_h = img.size
    draw = ImageDraw.Draw(img)

    data = load_json(json_path)
    items = get_items(data)

    # 좌표계 판별
    space = guess_coord_space(items, orig_w, orig_h)
    det_params = data.get("text_det_params", {})  # JSON에 있으면 활용
    s = det_scale_from_params(orig_w, orig_h, det_params)

    print("ORIG size:", (orig_w, orig_h))
    print("coord space guess:", space)
    print("det scale from params:", s)

    cache: Dict[str, str] = {}
    replaced = 0

    for it in items:
        ko = keep_korean_only(it["text"])
        if not ko:
            continue

        en = cache.get(ko)
        if en is None:
            en = ko_to_en(ko)
            cache[ko] = en
        if not en:
            continue

        # bbox/poly를 원본 좌표로 변환
        raw_box = it["bbox"]
        raw_poly = it.get("poly")

        if space == "orig" or s == 1.0:
            x1, y1, x2, y2 = map(int, map(round, raw_box))
            poly_pts = [(int(round(p[0])), int(round(p[1]))) for p in raw_poly] if raw_poly else None
        else:
            x1, y1, x2, y2 = map_box_scaled_to_orig(raw_box, s)
            poly_pts = map_poly_scaled_to_orig(raw_poly, s) if raw_poly else None

        # 원문 지우기(poly가 있으면 정확하게 polygon으로)
        if poly_pts and len(poly_pts) >= 4:
            draw.polygon(poly_pts, fill=(255, 255, 255))
        else:
            draw.rectangle([x1, y1, x2, y2], fill=(255, 255, 255))

        box_w = max(1, x2 - x1)
        box_h = max(1, y2 - y1)

        font, lines = fit_text(draw, en, box_w, box_h, font_path)

        pad = 4
        gap = 2
        line_h = text_bbox(draw, "Ag", font)[1]
        total_h = len(lines) * line_h + (len(lines) - 1) * gap

        cur_y = y1 + max(pad, (box_h - total_h) // 2)
        for ln in lines:
            ln_w, _ = text_bbox(draw, ln, font)
            cur_x = x1 + max(pad, (box_w - ln_w) // 2)
            draw.text((cur_x, cur_y), ln, fill=(0, 0, 0), font=font)
            cur_y += line_h + gap

        replaced += 1

    out_path.parent.mkdir(exist_ok=True)
    img.save(out_path)
    print("Saved:", out_path)
    print("Replaced:", replaced, "cache:", len(cache))


# -------------------------
# 7) 실행(메타 기반 권장)
# -------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--meta", type=str, default="", help="ocr_run_save_original.py가 만든 *_run_meta.json 경로")
    parser.add_argument("--img", type=str, default="", help="(옵션) 원본 이미지 경로 직접 지정")
    parser.add_argument("--json", type=str, default="", help="(옵션) OCR json 경로 직접 지정")
    parser.add_argument("--out", type=str, default="", help="(옵션) 출력 이미지 경로")
    parser.add_argument("--font", type=str, default=r"C:\Windows\Fonts\arial.ttf", help="영문 폰트 경로")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent

    if args.meta:
        meta = load_json(Path(args.meta).resolve())
        img_path = Path(meta["input_image"]).resolve()
        json_path = Path(meta["json_path"]).resolve()
        out_dir = Path(meta["out_dir"]).resolve()
        out_path = Path(args.out).resolve() if args.out else (out_dir / f"{img_path.stem}_translated_replace_on_original.jpg").resolve()
    else:
        if not args.img or not args.json:
            raise RuntimeError("--meta를 쓰거나, --img와 --json을 함께 지정해야 합니다.")
        img_path = Path(args.img).resolve()
        json_path = Path(args.json).resolve()
        out_path = Path(args.out).resolve() if args.out else (base / "ocr_output" / f"{img_path.stem}_translated_replace_on_original.jpg").resolve()

    replace_on_original(
        original_image_path=img_path,
        json_path=json_path,
        out_path=out_path,
        font_path=args.font,
    )
