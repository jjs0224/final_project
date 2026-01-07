from pathlib import Path
import os
import json
from typing import Optional, Dict, Any

import cv2
from paddleocr import PaddleOCR

# Optional preprocess (geometry-invariant)
try:
    from AI.preprocess_korean_menu import PreprocessConfig, preprocess_menu_image
except Exception:
    try:
        from preprocess_korean_menu import PreprocessConfig, preprocess_menu_image
    except Exception:
        PreprocessConfig = None  # type: ignore
        preprocess_menu_image = None  # type: ignore


def latest_file(dir_path: Path, pattern: str) -> Optional[Path]:
    files = list(dir_path.glob(pattern))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def _save_predict_results(results, out_dir: Path, stem: str) -> Path:
    """
    - save_to_json 지원 시: 그걸 우선 사용
    - 미지원 시: results raw dump
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(results, (list, tuple)) and len(results) > 0:
        first = results[0]
        if hasattr(first, "save_to_json"):
            first.save_to_json(str(out_dir))
            saved = latest_file(out_dir, "*.json")
            if saved is None:
                raise RuntimeError("save_to_json() 호출 후 json 파일을 찾지 못했습니다.")
            return saved

    json_path = out_dir / f"{stem}_ocr.json"
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return json_path


def run_ocr_and_save_json(
    image_path: Path,
    out_root: Path,
    det_limit_side_len: int = 4000,
    det_limit_type: str = "max",
    use_pre_rectify: bool = True,
    use_preprocess: bool = True,                  # ✅ 추가
    preprocess_mode: str = "clahe_denoise_sharp", # ✅ 추가 (파일 기본과 동일)
) -> Dict[str, Any]:
    image_path = Path(image_path)
    out_root = Path(out_root)

    # ✅ 항상 이미지별 폴더 생성
    out_dir = (out_root / image_path.stem).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rectify_meta: Dict[str, Any] = {"rectify": {"enabled": False}}
    preprocess_meta: Dict[str, Any] = {"preprocess": {"enabled": False}}

    # 1) 입력 로드
    img_bgr = cv2.imread(str(image_path))
    if img_bgr is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    # 2) (선택) rectify: 기하 보정 (기존 함수가 core에 있다면 그대로 사용)
    #    - 만약 현재 core가 "path 기반 rectify_document_image()"를 쓰는 구조면 그 방식 유지하세요.
    # 예) ocr_input_path, rectify_meta = rectify_document_image(image_path=image_path, out_dir=out_dir, min_area_ratio=0.20)
    # 여기서는 "img_bgr 기반"이 아니라는 전제하에, 당신 기존 코드 흐름에 맞춰 작성하세요.

    ocr_input_img = img_bgr
    ocr_input_path = image_path  # 메타용

    if use_pre_rectify:
        # ✅ 당신 파일에 이미 있는 rectify_document_image(path->path) 흐름을 쓰는 경우:
        # rectified_path, rectify_meta = rectify_document_image(image_path=image_path, out_dir=out_dir, min_area_ratio=0.20)
        # ocr_input_path = rectified_path
        # ocr_input_img = cv2.imread(str(rectified_path))

        # 또는 img_bgr 기반 rectify 로직이 있으면 그걸로 대체
        pass

    # 3) (선택) preprocess_korean_menu: 좌표 불변 픽셀 전처리
    if use_preprocess:
        if PreprocessConfig is None or preprocess_menu_image is None:
            raise ImportError(
                "preprocess_korean_menu.py 를 import할 수 없습니다. "
                "AI/preprocess_korean_menu.py 위치/모듈 경로를 확인하세요."
            )

        cfg = PreprocessConfig(mode=preprocess_mode, output="bgr")
        ocr_input_img = preprocess_menu_image(ocr_input_img, cfg)

        pre_path = out_dir / f"{image_path.stem}_pre_{preprocess_mode}.jpg"
        cv2.imwrite(str(pre_path), ocr_input_img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

        preprocess_meta = {
            "preprocess": {
                "enabled": True,
                "mode": preprocess_mode,
                "method": "geometry_invariant_pixel_only",
                "preprocessed_image": str(pre_path),
            }
        }

    # 4) PaddleOCR (predict)
    ocr = PaddleOCR(
        lang="korean",
        use_textline_orientation=True,
        use_doc_unwarping=False,
        det_limit_type=det_limit_type,
        det_limit_side_len=det_limit_side_len,
    )

    results = ocr.predict(ocr_input_img)  # ✅ img ndarray로 호출 (cls 금지)
    json_path = _save_predict_results(results, out_dir=out_dir, stem=image_path.stem)

    # 5) meta 저장
    meta: Dict[str, Any] = {
        "input_image_original": str(image_path),
        "input_image_for_ocr": str(ocr_input_path),
        "json_path": str(json_path),
        "out_dir": str(out_dir),
        "out_root": str(out_root),
        "paddleocr_config": {
            "use_doc_unwarping": False,
            "use_textline_orientation": True,
            "det_limit_type": det_limit_type,
            "det_limit_side_len": det_limit_side_len,
        },
    }
    meta.update(rectify_meta)
    meta.update(preprocess_meta)

    meta_path = out_dir / f"{image_path.stem}_run_meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    meta["meta_path"] = str(meta_path)

    return meta



if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    image_path = (BASE_DIR / "Upload_Images" / "image1.jpg").resolve()
    out_root = (BASE_DIR / "ocr_output").resolve()

    run_ocr_and_save_json(
        image_path=image_path,
        out_root=out_root,
        det_limit_side_len=4000,
        det_limit_type="max",
        use_pre_rectify=True,
    )
