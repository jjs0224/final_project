from __future__ import annotations

from pathlib import Path
import os
import json
from typing import Optional, Tuple, Dict, Any

import numpy as np
import cv2
from paddleocr import PaddleOCR

#최근파일중에서 최근 수정한 파일을 선택할때 사용한다.
def latest_file(dir_path: Path, pattern: str) -> Optional[Path]:
    files = list(dir_path.glob(pattern))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


# =========================================================
# 1) Document pre-warp (PaddleOCR 이전 보정 단계)
# =========================================================
def _order_points(pts: np.ndarray) -> np.ndarray:
    """
    pts: (4,2) - contour points
    return: ordered (tl, tr, br, bl)
    """
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)          # x+y
    diff = np.diff(pts, axis=1)  # x-y

    rect[0] = pts[np.argmin(s)]       # top-left
    rect[2] = pts[np.argmax(s)]       # bottom-right
    rect[1] = pts[np.argmin(diff)]    # top-right
    rect[3] = pts[np.argmax(diff)]    # bottom-left
    return rect


def _four_point_transform(image: np.ndarray, pts: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns: warped_image, H (orig->warp), H_inv (warp->orig)
    """
    rect = _order_points(pts)
    (tl, tr, br, bl) = rect

    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxW = int(max(widthA, widthB))

    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxH = int(max(heightA, heightB))

    dst = np.array([
        [0, 0],
        [maxW - 1, 0],
        [maxW - 1, maxH - 1],
        [0, maxH - 1]
    ], dtype=np.float32)

    H = cv2.getPerspectiveTransform(rect, dst)      # orig -> warp
    H_inv = cv2.getPerspectiveTransform(dst, rect)  # warp -> orig
    warped = cv2.warpPerspective(image, H, (maxW, maxH))
    return warped, H, H_inv


def rectify_document_image(
    image_path: Path,
    out_dir: Path,
    min_area_ratio: float = 0.20,
) -> Tuple[Path, Dict[str, Any]]:
    """
    메뉴판/문서가 찍힌 사진을 '퍼스펙티브 보정'하여 OCR 좌표계를 안정화.
    - 성공: 보정 이미지 저장 + H/H_inv 반환
    - 실패: 원본 그대로 사용 + H/H_inv = None
    """
    out_dir.mkdir(exist_ok=True)

    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(f"이미지를 읽을 수 없습니다: {image_path}")

    orig_h, orig_w = img.shape[:2]
    orig_area = float(orig_w * orig_h)

    # 처리 속도용 리사이즈(검출만 줄이고, 변환은 원본 스케일로 적용)
    target = 1200
    scale = target / max(orig_w, orig_h) if max(orig_w, orig_h) > target else 1.0
    small = cv2.resize(img, (int(orig_w * scale), int(orig_h * scale)), interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(gray, 60, 180)
    edges = cv2.dilate(edges, None, iterations=2)
    edges = cv2.erode(edges, None, iterations=1)

    cnts, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:10]

    doc_quad = None
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)  # 4각형 근사
        if len(approx) == 4:
            area = cv2.contourArea(approx)
            if area / (small.shape[0] * small.shape[1]) >= min_area_ratio:
                doc_quad = approx.reshape(4, 2).astype(np.float32)
                break

    # 보정 실패 → 원본 반환
    if doc_quad is None:
        meta = {
            "rectify": {
                "enabled": True,
                "status": "no_quad_found",
                "method": "opencv_contour_perspective",
                "scale_used_for_detection": scale,
                "H": None,
                "H_inv": None,
                "rectified_image": str(image_path),
            }
        }
        return image_path, meta

    # small 좌표 → orig 좌표로 복원
    doc_quad_orig = doc_quad / scale

    warped, H, H_inv = _four_point_transform(img, doc_quad_orig)

    rectified_path = out_dir / f"{image_path.stem}_rectified.jpg"
    cv2.imwrite(str(rectified_path), warped, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

    meta = {
        "rectify": {
            "enabled": True,
            "status": "ok",
            "method": "opencv_contour_perspective",
            "scale_used_for_detection": scale,
            "quad_orig_xy": doc_quad_orig.tolist(),
            "H": H.tolist(),         # orig -> rectified
            "H_inv": H_inv.tolist(), # rectified -> orig
            "rectified_image": str(rectified_path),
            "orig_image": str(image_path),
        }
    }
    return rectified_path, meta


# =========================================================
# 2) OCR 실행 + JSON 저장 + meta 저장
# =========================================================
def run_ocr_and_save_json(
    image_path: Path,
    out_dir: Path,
    det_limit_side_len: int = 4000,
    det_limit_type: str = "max",
    use_pre_rectify: bool = True,
) -> dict:
    """
    - (추가) use_pre_rectify=True면 PaddleOCR 이전에 이미지 퍼스펙티브 보정 수행
    - use_doc_unwarping=False 고정 (PaddleOCR 내부 보정 OFF)
    """
    out_dir.mkdir(exist_ok=True)

    print("CWD:", os.getcwd())
    print("IMAGE (original):", image_path)
    print("EXISTS:", image_path.exists())

    # 1) Pre-rectify (원본->보정 이미지로 OCR 수행)
    rectify_meta: Dict[str, Any] = {"rectify": {"enabled": False}}
    ocr_input_path = image_path

    if use_pre_rectify:
        ocr_input_path, rectify_meta = rectify_document_image(
            image_path=image_path,
            out_dir=out_dir,
            min_area_ratio=0.20,   # 메뉴판이 화면에서 차지하는 비율이 작으면 낮추세요(예: 0.12)
        )

    print("IMAGE (for OCR):", ocr_input_path)

    # 2) PaddleOCR
    ocr = PaddleOCR(
        lang="korean",
        use_textline_orientation=True,
        use_doc_unwarping=False,      # ✅ 내부 문서 펴기(off) 유지
        det_limit_type=det_limit_type,
        det_limit_side_len=det_limit_side_len,
    )

    results = ocr.predict(str(ocr_input_path))

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

    # 3) meta 저장: 원본/보정/OCR입력/변환행렬 포함
    meta = {
        "input_image_original": str(image_path),
        "input_image_for_ocr": str(ocr_input_path),
        "json_path": str(json_path),
        "out_dir": str(out_dir),
        "paddleocr_config": {
            "use_doc_unwarping": False,
            "use_textline_orientation": True,
            "det_limit_type": det_limit_type,
            "det_limit_side_len": det_limit_side_len,
        },
    }
    meta.update(rectify_meta)

    meta_path = out_dir / f"{image_path.stem}_run_meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    meta["meta_path"] = str(meta_path)

    print("\n=== SAVED ===")
    print("JSON :", json_path.name)
    print("META :", meta_path.name)
    if meta.get("rectify", {}).get("enabled"):
        print("RECT:", Path(meta["rectify"]["rectified_image"]).name)

    return meta


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    img_dir = (BASE_DIR / "Upload_Images").resolve()
    out_dir = (BASE_DIR / "ocr_output").resolve()

    # 폴더 내 모든 이미지 처리 (png/jpg/jpeg/webp/bmp)
    exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    if not img_dir.exists():
        raise FileNotFoundError(f"Image folder not found: {img_dir}")

    image_paths = sorted([p for p in img_dir.iterdir() if p.is_file() and p.suffix.lower() in exts])
    if not image_paths:
        raise RuntimeError(f"No images found in: {img_dir}")

    ok, fail = 0, 0
    for image_path in image_paths:
        print("\n" + "=" * 60)
        print(f"[RUN] {image_path.name}")
        try:
            run_ocr_and_save_json(
                image_path=image_path,
                out_dir=out_dir,
                det_limit_side_len=4000,
                det_limit_type="max",
                use_pre_rectify=True,   # ✅ True면 사전 기하 보정(퍼스펙티브) 적용
            )
            ok += 1
        except Exception as e:
            fail += 1
            print(f"[FAIL] {image_path.name}: {e}")

    print("\n" + "=" * 60)
    print(f"Done. success={ok}, failed={fail}, total={len(image_paths)}")
