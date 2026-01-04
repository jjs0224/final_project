from __future__ import annotations

from pathlib import Path
import json
import re
from typing import Any, List, Tuple, Dict, Optional

from PIL import Image, ImageDraw, ImageFont

# =========================
# 1) 입력/출력 경로 설정
# =========================
BASE_DIR = Path(__file__).resolve().parent
IMAGE_PATH = (BASE_DIR / "Upload_Images" / "image_1.jpg").resolve()
JSON_PATH  = (BASE_DIR / "ocr_output" / "image_1_res.json").resolve()  # 당신이 저장한 JSON 경로로 맞추세요
OUT_PATH   = (BASE_DIR / "ocr_output" / "image_1_translated_replace.jpg").resolve()
OUT_PATH.parent.mkdir(exist_ok=True)

# =========================
# 2) 한글만 추출
#    - 숫자/영문/기호 제거
# =========================
def keep_korean_only(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip()
    # 완성형 한글 + 공백만 남김
    s = re.sub(r"[^가-힣\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

# =========================
# 3) 번역기 (선택 1: OpenAI API / 선택 2: 로컬 HuggingFace)
#    - 여기서는 "로컬 HuggingFace" 예시를 기본으로 둡니다.
#    - 인터넷이 막혀 있거나 모델 다운로드가 어려우면, 당신 환경에 맞춰 API 방식으로 바꿔드릴 수 있습니다.
# =========================
def build_translator():
    """
    로컬 번역 파이프라인 (HuggingFace)
    설치:
      pip install transformers sentencepiece torch
    """
    try:
        from transformers import pipeline
        return pipeline("translation", model="Helsinki-NLP/opus-mt-ko-en")
    except Exception as e:
        raise RuntimeError(
            "번역기 로드 실패. transformers/sentencepiece/torch 설치 및 모델 다운로드가 필요합니다.\n"
            f"원인: {e}"
        )

translator = build_translator()

def ko_to_en(text: str) -> str:
    if not text:
        return ""
    out = translator(text, max_length=128)
    return out[0]["translation_text"].strip()

# =========================
# 4) JSON 파싱: rec_texts + 좌표(polys/boxes) 매칭
# =========================
def load_ocr_json(json_path: Path) -> dict:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return data

def poly_to_bbox(poly: List[List[float]]) -> Tuple[int, int, int, int]:
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))

def get_items_from_json(data: dict) -> List[dict]:
    """
    PaddleOCR JSON(당신 파일 구조) 기준:
      - rec_texts: [str, ...]
      - rec_polys: [[[x,y]...], ...]  (4점 폴리곤)
      - rec_boxes: [[x1,y1,x2,y2], ...] (xmin,ymin,xmax,ymax)
    """
    texts = data.get("rec_texts", [])
    polys = data.get("rec_polys", None)
    boxes = data.get("rec_boxes", None)

    items = []
    n = len(texts)

    for i in range(n):
        t = texts[i] if i < len(texts) else ""
        poly = polys[i] if polys and i < len(polys) else None
        box = boxes[i] if boxes and i < len(boxes) else None

        # bbox 우선순위: rec_boxes > rec_polys
        if box and len(box) == 4:
            x1, y1, x2, y2 = map(int, box)
            bbox = (x1, y1, x2, y2)
        elif poly:
            bbox = poly_to_bbox(poly)
        else:
            # 좌표 없으면 스킵(위치 표시 불가)
            continue

        items.append({"text": t, "poly": poly, "bbox": bbox})

    return items

# =========================
# 5) 자동 줄바꿈 + 폰트 크기 자동 조절
# =========================
def text_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> Tuple[int, int]:
    # (w, h) 반환
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    return (r - l), (b - t)

def wrap_text_to_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int
) -> List[str]:
    """
    단어 기준 줄바꿈 (영문 기준)
    """
    words = text.split()
    if not words:
        return []

    lines: List[str] = []
    cur = words[0]
    for w in words[1:]:
        trial = cur + " " + w
        w_trial, _ = text_bbox(draw, trial, font)
        if w_trial <= max_width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines

def fit_text_in_box(
    draw: ImageDraw.ImageDraw,
    text: str,
    box_w: int,
    box_h: int,
    font_path: str,
    max_font_size: int = 28,
    min_font_size: int = 10,
    pad: int = 4,
    line_gap: int = 2,
) -> Tuple[ImageFont.FreeTypeFont, List[str]]:
    """
    박스 크기에 맞도록:
      - 폰트 크기 내림
      - 줄바꿈 수행
      - 전체 높이/폭이 박스 안에 들어올 때까지 반복
    """
    target_w = max(1, box_w - 2 * pad)
    target_h = max(1, box_h - 2 * pad)

    for size in range(max_font_size, min_font_size - 1, -1):
        font = ImageFont.truetype(font_path, size)
        lines = wrap_text_to_width(draw, text, font, target_w)

        if not lines:
            continue

        # 가장 긴 줄 폭
        max_line_w = max(text_bbox(draw, ln, font)[0] for ln in lines)
        # 총 높이
        line_h = text_bbox(draw, "Ag", font)[1]  # 대략 높이
        total_h = len(lines) * line_h + (len(lines) - 1) * line_gap

        if max_line_w <= target_w and total_h <= target_h:
            return font, lines

    # 끝까지 못 맞추면 최소 폰트로 강행
    font = ImageFont.truetype(font_path, min_font_size)
    lines = wrap_text_to_width(draw, text, font, max(1, box_w - 2 * pad))
    return font, lines

# =========================
# 6) 이미지에 "한글 대신" 번역문으로 교체 렌더링
# =========================
def replace_korean_with_translation(
    image_path: Path,
    json_path: Path,
    out_path: Path,
    font_path: Optional[str] = None,
    score_thresh: float = 0.0,  # 필요시 rec_scores 기반 필터링하려면 확장 가능
):
    if not image_path.exists():
        raise FileNotFoundError(f"이미지 파일이 없습니다: {image_path}")
    if not json_path.exists():
        raise FileNotFoundError(f"JSON 파일이 없습니다: {json_path}")

    # 폰트(영문)
    # Windows 예시: C:\Windows\Fonts\arial.ttf
    # macOS: /System/Library/Fonts/Supplemental/Arial.ttf
    # Linux: /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
    if font_path is None:
        # Windows 기본값(당신 환경이 Windows인 로그가 있었음)
        font_path = r"C:\Windows\Fonts\arial.ttf"

    data = load_ocr_json(json_path)
    items = get_items_from_json(data)

    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    # 번역 캐시(같은 한글 문구 반복 번역 방지)
    cache: Dict[str, str] = {}

    replaced_count = 0

    for it in items:
        raw = it["text"]
        bbox = it["bbox"]  # (x1,y1,x2,y2)
        poly = it.get("poly")

        ko = keep_korean_only(raw)
        if not ko:
            continue  # 한글이 없으면 교체 대상 아님

        # 번역
        if ko in cache:
            en = cache[ko]
        else:
            en = ko_to_en(ko)
            cache[ko] = en

        if not en:
            continue

        x1, y1, x2, y2 = bbox
        box_w = max(1, x2 - x1)
        box_h = max(1, y2 - y1)

        # 1) 원본 한글 "지우기": 폴리곤이 있으면 폴리곤, 없으면 bbox 사각형 덮기
        #    - 메뉴판 배경이 흰색/밝은색이 많아서 일단 흰색으로 덮습니다.
        if poly and isinstance(poly, list) and len(poly) >= 4:
            draw.polygon([(p[0], p[1]) for p in poly], fill=(255, 255, 255))
        else:
            draw.rectangle([x1, y1, x2, y2], fill=(255, 255, 255))

        # 2) 박스에 맞춰 폰트 + 줄바꿈 결정
        font, lines = fit_text_in_box(
            draw=draw,
            text=en,
            box_w=box_w,
            box_h=box_h,
            font_path=font_path,
            max_font_size=28,
            min_font_size=10,
            pad=4,
            line_gap=2
        )

        # 3) 박스 내부에 배치(세로 중앙 정렬)
        pad = 4
        line_gap = 2
        line_h = text_bbox(draw, "Ag", font)[1]
        total_h = len(lines) * line_h + (len(lines) - 1) * line_gap

        cur_y = y1 + max(pad, (box_h - total_h) // 2)
        for ln in lines:
            ln_w, _ = text_bbox(draw, ln, font)
            cur_x = x1 + max(pad, (box_w - ln_w) // 2)  # 가로 중앙 정렬
            draw.text((cur_x, cur_y), ln, fill=(0, 0, 0), font=font)
            cur_y += line_h + line_gap

        replaced_count += 1

    img.save(out_path)
    print(f"Saved: {out_path}")
    print(f"Replaced boxes: {replaced_count}")
    print(f"Translation cache size: {len(cache)}")

# =========================
# 7) 실행
# =========================
if __name__ == "__main__":
    replace_korean_with_translation(
        image_path=IMAGE_PATH,
        json_path=JSON_PATH,
        out_path=OUT_PATH,
        font_path=r"C:\Windows\Fonts\arial.ttf",  # 필요시 변경
    )
