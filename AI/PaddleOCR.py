from pathlib import Path
import os
import re
import json
from typing import Any, Optional

from paddleocr import PaddleOCR

# -----------------------------
# 1) Text normalization
# -----------------------------
import re

def normalize_ocr_text(texts: list[str]) -> str:
    """
    OCR 텍스트 리스트에서
    오직 '한글 + 공백'만 남기고 정제
    """
    cleaned: list[str] = []

    for t in texts:
        if not isinstance(t, str):
            continue

        t = t.strip()

        # 1) 한글과 공백만 남기고 전부 제거
        t = re.sub(r"[^가-힣\s]", "", t)

        # 2) 중복 공백 제거
        t = re.sub(r"\s+", " ", t)

        t = t.strip()
        if t:
            cleaned.append(t)

    return "\n".join(cleaned)

# -----------------------------
# 2) JSON에서 텍스트를 재귀적으로 수집
#    (PaddleOCR 버전/스키마 차이를 최대한 흡수)
# -----------------------------
TEXT_KEYS = {
    "text", "texts",
    "rec_text", "rec_texts",
    "transcription", "transcriptions",
    "ocr_text", "ocr_texts",
}

def collect_texts_from_json(obj: Any) -> list[str]:
    """
    JSON(dict/list/primitive)을 재귀 순회하며 텍스트로 보이는 값들을 수집
    """
    out: list[str] = []

    if isinstance(obj, dict):
        for k, v in obj.items():
            # 키가 text 계열이면 우선 수집
            if isinstance(k, str) and k.lower() in TEXT_KEYS:
                if isinstance(v, str):
                    out.append(v)
                elif isinstance(v, list):
                    out.extend([x for x in v if isinstance(x, str)])

            # 계속 재귀 탐색
            out.extend(collect_texts_from_json(v))

    elif isinstance(obj, list):
        for item in obj:
            out.extend(collect_texts_from_json(item))

    return out

def get_latest_json(out_dir: Path) -> Optional[Path]:
    """
    out_dir 내에서 가장 최근 수정된 json 파일 경로 반환
    """
    json_files = list(out_dir.glob("*.json"))
    if not json_files:
        return None
    return max(json_files, key=lambda p: p.stat().st_mtime)

# -----------------------------
# 3) Main
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
image_path = (BASE_DIR / "Upload_Images" / "image_1.jpg").resolve()

print("CWD:", os.getcwd())
print("SCRIPT:", BASE_DIR)
print("IMAGE:", image_path)
print("EXISTS:", image_path.exists())

# 결과 저장 폴더
out_dir = BASE_DIR / "ocr_output"
out_dir.mkdir(exist_ok=True)

ocr = PaddleOCR(
    lang="korean",
    use_textline_orientation=True,
)

print("\n=== PREDICT START ===")
results = ocr.predict(str(image_path))  # 최신 권장 API (iterable/generator 가능)

got_any = False
texts: list[str] = []

for i, res in enumerate(results, start=1):
    got_any = True
    print(f"\n--- RESULT #{i} ---")

    # (선택) 콘솔 출력
    if hasattr(res, "print"):
        res.print()

    # JSON 저장 → 저장된 JSON에서 텍스트 추출(핵심 해결방안)
    if hasattr(res, "save_to_json"):
        # save_to_json이 내부적으로 파일명을 결정하므로, 저장 후 최신 파일을 잡는다.
        res.save_to_json(str(out_dir))
        latest = get_latest_json(out_dir)

        if latest is None:
            print("WARN: JSON 파일을 찾지 못했습니다.")
        else:
            try:
                data = json.loads(latest.read_text(encoding="utf-8"))
                extracted = collect_texts_from_json(data)
                texts.extend(extracted)
                print("Saved JSON:", latest.name, "| extracted_texts:", len(extracted))
            except Exception as e:
                print("WARN: JSON 파싱/추출 실패:", e)

    # (선택) 시각화 이미지 저장
    if hasattr(res, "save_to_img"):
        res.save_to_img(str(out_dir))
        print("Saved IMG to:", out_dir)

print("\n=== PREDICT END ===")
if not got_any:
    print("결과 객체가 하나도 생성되지 않았습니다. (pipeline 출력이 비어 있음)")
else:
    print("texts_count:", len(texts))
    final_text = normalize_ocr_text(texts)
    print("\n=== NORMALIZED TEXT ===")
    print(final_text if final_text else "(빈 결과: 텍스트가 추출되지 않았습니다.)")
