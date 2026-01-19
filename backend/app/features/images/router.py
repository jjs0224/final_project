from fastapi import APIRouter, UploadFile, File, HTTPException
from ai.review.pipeline.receipt_service import process_receipt_ocr
import traceback

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post("/receipt")
async def receipt_ocr(image: UploadFile = File(...)):
    try:
        print("[DEBUG] endpoint hit")
        print("[DEBUG] filename:", image.filename)
        print("[DEBUG] content_type:", image.content_type)

        contents = await image.read()

        print("[DEBUG] image bytes:", len(contents))

        # temp_path = "temp.jpg"
        # with open(temp_path, "wb") as f:
        #     f.write(contents)
        #
        # print("[DEBUG] image saved:", temp_path)

        result = process_receipt_ocr(contents)

        print("[DEBUG] OCR result type:", type(result))

        return result

    except Exception as e:
        print("🔥 OCR ERROR 🔥")
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )
    return result