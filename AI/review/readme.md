C:\Users\201\Desktop\final_project\ai\review> 

python -c "from pathlib import Path; from receipt_service import process_receipt_ocr; preprocess_image(Path('tmp_receipt/receipt_5.jpg').read_bytes())"

-receipt -> OCR_raw.json
python -c "from pathlib import Path; from review.receipt_service import process_receipt_ocr; process_receipt_ocr(Path('review/tmp_receipt/receipt_7.jpg').read_bytes())"
