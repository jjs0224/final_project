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
            use_textline_orientation=True,
            use_doc_unwarping=True,
            text_det_limit_side_len=1280,
            text_det_thresh=0.3,
            text_det_box_thresh=0.2,
            text_det_unclip_ratio=1.5,
            enable_mkldnn=False,  # 핵심
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

def draw_ocr_boxes(image: np.ndarray, ocr_result, save_path="ocr_bbox.png"):
    """
    image: 원본 or 전처리된 이미지 (BGR)
    ocr_result: result[0] (dict with rec_polys, rec_texts)
    """
    vis = image.copy()

    polys = ocr_result["rec_polys"]
    texts = ocr_result["rec_texts"]

    for poly, text in zip(polys, texts):
        poly = poly.astype(int)

        # bbox polygon
        cv2.polylines(
            vis,
            [poly],
            isClosed=True,
            color=(0, 255, 0),
            thickness=2
        )

        # text label (왼쪽 위)
        x, y = poly[0]
        cv2.putText(
            vis,
            text[:10],
            (x, y - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            1,
            cv2.LINE_AA
        )

    cv2.imwrite(save_path, vis)
    print(f"[DEBUG] OCR bbox image saved → {save_path}")

def ocr_result_to_json_safe(ocr_item: dict) -> dict:
    tokens = []

    texts = ocr_item.get("rec_texts", [])
    polys = ocr_item.get("rec_polys", [])

    for text, poly in zip(texts, polys):
        tokens.append({
            "text": text,
            "bbox": poly.astype(float).tolist()
        })

    return {
        "tokens": tokens
    }

def process_receipt_ocr(image_bytes: bytes) -> dict:
    ocr = get_ocr()
    # img = preprocess_size(image_bytes)
    img = preprocess_image(image_bytes)

    result = ocr.predict(img)

    if not result or not result[0]:
        return {"error": "No text detected"}

    ocr_raw = ocr_result_to_json_safe(result[0])
    with open("ocr_result.json", "w", encoding="utf-8") as f:
        json.dump(ocr_raw, f, ensure_ascii=False, indent=2)
        print("ocr_result.json saved")

    receipt = build_receipt_json(result[0])

    draw_ocr_boxes(
        image=img,
        ocr_result=result[0],
        save_path="../ocr_bbox.png"
    )
    # with open("receipt_result.json", "w", encoding="utf-8") as f:
    #
    #     json.dump(receipt, f, ensure_ascii=False, indent=2)
    #     print("receipt_to_store.json saved")
    #
    # return receipt

    print(receipt)
