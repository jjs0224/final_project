from fastapi import APIRouter, UploadFile, File, HTTPException
from ai.review.receipt_service import process_receipt_ocr

router = APIRouter(prefix="/receipts", tags=["receipt"])

@router.post("/receipt")
async def ocr_receipt(image: UploadFile = File(...)):
    if not image.content_type.startswith("image/"):
        raise HTTPException(400, "Invalid image")

    image_bytes = await image.read()
    return process_receipt_ocr(image_bytes)
