from paddleocr import PaddleOCR
from .receipt_preprocess import preprocess_image
from .receipt_parser import build_receipt_json
import json
import cv2
import numpy as np


_ocr = None

def get_ocr():
    global _ocr
    if _ocr is None:
        print("OCR INIT: PaddleOCR initializing...")
        _ocr = PaddleOCR(
            lang="korean",
            use_angle_cls=True,
            use_doc_unwarping=True,
            det_limit_side_len=3000,
            det_db_thresh=0.1,
            det_db_box_thresh=0.2,
            det_db_unclip_ratio=2.0
        )
    return _ocr

def preprocess_size(image_bytes: bytes, max_side=1600):
    img_array = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Failed to decode image")

    h, w = img.shape[:2]
    max_dim = max(h, w)

    if max_dim > max_side:
        scale = max_side / max_dim
        new_w = int(w * scale)
        new_h = int(h * scale)

        img = cv2.resize(
            img,
            (new_w, new_h),
            interpolation=cv2.INTER_AREA
        )

        print(f"[DEBUG] resized image → {new_w}x{new_h}")

    else:
        print(f"[DEBUG] image size OK → {w}x{h}")

    return img

def process_receipt_ocr(image_bytes: bytes) -> dict:
    ocr = get_ocr()
    # img = preprocess_size(image_bytes)
    img = preprocess_image(image_bytes)

    result = ocr.predict(img)

    if not result or not result[0]:
        return {"error": "No text detected"}

    receipt = build_receipt_json(result[0])

    with open("receipt_result.json", "w", encoding="utf-8") as f:

        json.dump(receipt, f, ensure_ascii=False, indent=2)
        print("receipt_to_store.json saved")

    return receipt
