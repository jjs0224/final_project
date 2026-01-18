from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np


@dataclass(frozen=True)
class PerspectiveRectifyParams:
    """
    Parameters for contour-based document/menu-board rectification.

    - canny1/canny2: edge thresholds
    - dilate_iter: dilation iterations for connecting edges
    - approx_eps_ratio: polygon approximation epsilon ratio vs contour perimeter
    - min_area_ratio: minimum contour area relative to image area to be considered
    - border: optional padding (pixels) added after warp (useful for OCR)
    """
    canny1: int = 50
    canny2: int = 150
    dilate_iter: int = 2
    approx_eps_ratio: float = 0.02
    min_area_ratio: float = 0.08
    border: int = 10


def _order_points(pts: np.ndarray) -> np.ndarray:
    # pts: (4,2)
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).reshape(-1)

    rect[0] = pts[np.argmin(s)]      # top-left
    rect[2] = pts[np.argmax(s)]      # bottom-right
    rect[1] = pts[np.argmin(diff)]   # top-right
    rect[3] = pts[np.argmax(diff)]   # bottom-left
    return rect


def _safe_int(x: float) -> int:
    return int(max(1, round(float(x))))


def find_document_quad(image_bgr: np.ndarray, params: PerspectiveRectifyParams) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
    """
    Find the largest plausible 4-point document/menu-board contour.
    Returns:
      - quad: np.ndarray (4,2) float32 in image coords, ordered (tl,tr,br,bl) OR None
      - meta: debug info for logging
    """
    h, w = int(image_bgr.shape[0]), int(image_bgr.shape[1])
    img_area = float(h * w)

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(gray, params.canny1, params.canny2)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=params.dilate_iter)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best = None
    best_area = 0.0

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < params.min_area_ratio * img_area:
            continue

        peri = cv2.arcLength(cnt, True)
        eps = params.approx_eps_ratio * peri
        approx = cv2.approxPolyDP(cnt, eps, True)

        if len(approx) != 4:
            continue

        if area > best_area:
            best_area = area
            best = approx

    meta: Dict[str, Any] = {
        "found": best is not None,
        "image_shape": [h, w],
        "num_contours": len(contours),
        "best_area": float(best_area),
        "min_area_ratio": params.min_area_ratio,
    }

    if best is None:
        return None, meta

    pts = best.reshape(4, 2).astype(np.float32)
    rect = _order_points(pts)
    meta["quad"] = rect.tolist()
    return rect, meta


def warp_perspective(image_bgr: np.ndarray, quad: np.ndarray, params: PerspectiveRectifyParams) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Warp image by the given quadrilateral (tl,tr,br,bl) into a fronto-parallel rectangle.
    """
    tl, tr, br, bl = quad

    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxW = _safe_int(max(widthA, widthB))

    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxH = _safe_int(max(heightA, heightB))

    dst = np.array([
        [0, 0],
        [maxW - 1, 0],
        [maxW - 1, maxH - 1],
        [0, maxH - 1]
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(quad.astype(np.float32), dst)
    warped = cv2.warpPerspective(image_bgr, M, (maxW, maxH))

    if params.border and params.border > 0:
        warped = cv2.copyMakeBorder(
            warped,
            params.border, params.border, params.border, params.border,
            borderType=cv2.BORDER_CONSTANT,
            value=(255, 255, 255),
        )

    meta: Dict[str, Any] = {
        "warp_size": [int(warped.shape[0]), int(warped.shape[1])],
        "matrix": M.tolist(),
        "border": int(params.border),
    }
    return warped, meta
