from paddleocr import PaddleOCR
from .receipt_preprocess import preprocess_image
from .receipt_parser import build_receipt_json
import json

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

    result = ocr.ocr(img, cls=True)

    if not result or not result[0]:
        return {"error": "No text detected"}

    receipt = build_receipt_json(result[0])

    with open("receipt_result.json", "w", encoding="utf-8") as f:

        json.dump(receipt, f, ensure_ascii=False, indent=2)
        print("receipt_to_store.json saved")

    return receipt
