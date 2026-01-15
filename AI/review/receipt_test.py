from pathlib import Path

from paddleocr import PaddleOCR
from ai.review.receipt_preprocess import preprocess_image
from ai.review.receipt_parser import build_receipt_json
import json

BASE_DIR = Path(__file__).resolve().parent              # model_testing
UPLOAD_DIR = BASE_DIR / "tmp_receipt"
OUTPUT_DIR = BASE_DIR / "tmp_output"

ocr = PaddleOCR(
    lang="korean",
    use_angle_cls=True,
    use_doc_unwarping=True,
    det_limit_side_len=3000,
    det_db_thresh=0.1,
    det_db_box_thresh=0.2,
    det_db_unclip_ratio=2.0
)

def process_receipt_ocr(image_bytes: bytes) -> dict:
    img = preprocess_image(image_bytes)

    result = ocr.predict(img)
    # print(result)

    if not result or not result[0]:
        return {"error": "No text detected"}

    receipt = build_receipt_json(result[0])

    with open("receipt_result.json", "w", encoding="utf-8") as f:

        json.dump(receipt, f, ensure_ascii=False, indent=2)
        print("receipt_to_store.json saved")

    return receipt

if __name__ == "__main__":
    #image_files = list(UPLOAD_DIR.glob("*.jpg")) + list(UPLOAD_DIR.glob("*.png"))
    image_files = UPLOAD_DIR.glob("receipt_10.jpg")
    if not image_files:
        raise FileNotFoundError("No receipt image found in Uploaded_Images")

    for image_file in image_files:  # image_file is now a string path
        with open(image_file, "rb") as f:
            image_bytes = f.read()
        process_receipt_ocr(image_bytes)

