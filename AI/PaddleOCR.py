from pathlib import Path
import os
import re
from paddleocr import PaddleOCR

def extract_texts_from_ocr(res) -> list[str]:#OCR로 변환된 text 추출
    """
    PaddleOCR 결과 객체(res)에서
    텍스트만 리스트 형태로 안전하게 추출
    """
    texts = []

    if hasattr(res, "texts"):
        texts = res.texts

    elif hasattr(res, "results"):
        # 일부 버전 호환
        for line in res.results:
            if len(line) >= 2:
                texts.append(line[1][0])

    return texts

def normalize_ocr_text(texts: list[str]) -> str:# 추출된 text 다듬기
    """
    OCR 텍스트 리스트를
    하나의 정제된 문자열로 변환
    """
    cleaned = []

    for t in texts:
        t = t.strip()                     # 앞뒤 공백 제거
        t = re.sub(r"\s+", " ", t)        # 중복 공백 제거
        t = t.replace("·", " ")           # 메뉴판 특수문자 제거
        cleaned.append(t)

    return "\n".join(cleaned)

BASE_DIR = Path(__file__).resolve().parent # 현재 파일의 상위폴더 즉 AI 폴더의 절대위치
image_path = (BASE_DIR / "Upload_Images" / "image_1.jpg").resolve()   # 지금 당신 로그에 맞춤

print("CWD:", os.getcwd())
print("SCRIPT:", BASE_DIR)
print("IMAGE:", image_path)
print("EXISTS:", image_path.exists())

ocr = PaddleOCR(
    lang="korean",
    use_textline_orientation=True,     # ✅ use_angle_cls 대신
)

print("\n=== PREDICT START ===")
results = ocr.predict(str(image_path))   # ✅ 최신 권장 API

got_any = False
texts = []
# ✅ predict()가 generator/iterable이면 반드시 순회해야 출력이 나옵니다.
for i, res in enumerate(results, start=1):
    got_any = True
    print(f"\n--- RESULT #{i} ---")

    # 1) 가장 확실: res.print() (문서/이슈에서 많이 쓰는 방식)
    if hasattr(res, "print"):
        res.print()

    # 2) JSON으로 저장/확인
    if hasattr(res, "save_to_json"):
        out_dir = BASE_DIR / "ocr_output"
        out_dir.mkdir(exist_ok=True)
        res.save_to_json(str(out_dir))   # ocr_output 폴더에 json 저장
        print("Saved JSON to:", out_dir)

    # 3) 시각화 이미지 저장(박스 그려진 결과)
    if hasattr(res, "save_to_img"):
        out_dir = BASE_DIR / "ocr_output"
        out_dir.mkdir(exist_ok=True)
        res.save_to_img(str(out_dir))
        print("Saved IMG to:", out_dir)

    text = extract_texts_from_ocr(res)
    texts = texts.append(text)
norm_texts = normalize_ocr_text(texts)
print(norm_texts)

print("\n=== PREDICT END ===")
if not got_any:
    print("결과 객체가 하나도 생성되지 않았습니다. (pipeline 출력이 비어 있음)")



