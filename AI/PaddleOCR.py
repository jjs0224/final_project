from __future__ import annotations

from pathlib import Path
import os
import json
from typing import Optional

from paddleocr import PaddleOCR


def latest_file(dir_path: Path, pattern: str) -> Optional[Path]:
    files = list(dir_path.glob(pattern))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def run_ocr_and_save_json(
    image_path: Path,
    out_dir: Path,
    det_limit_side_len: int = 4000,
    det_limit_type: str = "max",
) -> dict:
    """
    - use_doc_unwarping=False 고정
    - det_limit_*로 검출 리사이즈를 가능한 억제(원본 큰 변보다 크게 설정 추천)
    - 결과 JSON과 메타 저장
    """
    out_dir.mkdir(exist_ok=True)

    print("CWD:", os.getcwd())
    print("IMAGE:", image_path)
    print("EXISTS:", image_path.exists())

    ocr = PaddleOCR(
        lang="korean",
        use_textline_orientation=True,
        use_doc_unwarping=False,      # ✅ 요청사항: 문서 펴기(off)
        det_limit_type=det_limit_type,
        det_limit_side_len=det_limit_side_len,
    )

    results = ocr.predict(str(image_path))

    got_any = False
    json_path: Optional[Path] = None

    for i, res in enumerate(results, start=1):
        got_any = True
        print(f"\n--- RESULT #{i} ---")

        if hasattr(res, "print"):
            res.print()

        if hasattr(res, "save_to_json"):
            res.save_to_json(str(out_dir))
            json_path = latest_file(out_dir, "*.json")
            break

        break

    if not got_any:
        raise RuntimeError("OCR 결과 객체가 생성되지 않았습니다.")
    if json_path is None:
        raise RuntimeError("JSON 저장 실패: save_to_json() 지원/권한/경로를 확인하세요.")

    meta = {
        "input_image": str(image_path),
        "json_path": str(json_path),
        "out_dir": str(out_dir),
        "paddleocr_config": {
            "use_doc_unwarping": False,
            "use_textline_orientation": True,
            "det_limit_type": det_limit_type,
            "det_limit_side_len": det_limit_side_len,
        },
    }

    meta_path = out_dir / f"{image_path.stem}_run_meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    meta["meta_path"] = str(meta_path)

    print("\n=== SAVED ===")
    print("JSON :", json_path.name)
    print("META :", meta_path.name)

    return meta


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    image_path = (BASE_DIR / "Upload_Images" / "image_1.jpg").resolve()
    out_dir = (BASE_DIR / "ocr_output").resolve()

    run_ocr_and_save_json(
        image_path=image_path,
        out_dir=out_dir,
        det_limit_side_len=4000,   # 원본 긴 변보다 크게 잡으면 리사이즈 억제됨
        det_limit_type="max",
    )
