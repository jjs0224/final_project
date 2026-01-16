from paddleocr import PaddleOCR

print("🔥 Loading OCR model once...")

ocr_model = PaddleOCR(
    lang="korean",
    use_angle_cls=True,
    use_doc_unwarping=True,
    det_limit_side_len=3000,
    det_db_thresh=0.1,
    det_db_box_thresh=0.2,
    det_db_unclip_ratio=2.0
)