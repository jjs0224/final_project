from __future__ import annotations

from typing import Any, Dict, Tuple
import cv2
import numpy as np

#입력이 컬러이미지면 gray로 변환한다.앞단에서 이미 회색이여도 작동하도록 한다.
def _safe_gray(image_bgr: np.ndarray) -> np.ndarray:
    if image_bgr.ndim == 3 and image_bgr.shape[2] == 3:
        return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    return image_bgr.copy()


def compute_dewarp_trigger(image_bgr: np.ndarray) -> Dict[str, Any]:
    """
    A lightweight "need dewarp?" signal without OCR.

    Intuition:
      - Curved/warped text tends to increase mixed-direction edges and line angle dispersion.
      - Flat, well-rectified menus often show strong horizontal structure after docunet.

    Returns:
      score: 0~1 (higher => more likely needs dewarp)
    """
    gray = _safe_gray(image_bgr)
    h, w = gray.shape[:2]

    # Downscale for speed/stability 대략판단.
    scale = 800.0 / max(h, w) if max(h, w) > 800 else 1.0
    if scale < 1.0:
        gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    # Edge map
    edges = cv2.Canny(gray, 50, 150)

    # Sobel energy ratio (orientation mixture)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    ex = float(np.mean(np.abs(gx)))
    ey = float(np.mean(np.abs(gy)))
    # If ex and ey are similar, structure is mixed (potential curvature or noisy scene)
    mix = 1.0 - abs(ex - ey) / (ex + ey + 1e-6)  # 0 (one dominates) ~ 1 (mixed)

    # Hough line angle dispersion (curvature -> angles spread)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80, minLineLength=40, maxLineGap=10)
    angles = []
    if lines is not None:
        for (x1, y1, x2, y2) in lines[:, 0]:
            dx, dy = (x2 - x1), (y2 - y1)
            if dx == 0 and dy == 0:
                continue
            ang = np.degrees(np.arctan2(dy, dx))
            # Normalize to [-90, 90]
            while ang < -90:
                ang += 180
            while ang > 90:
                ang -= 180
            angles.append(ang)

    if len(angles) >= 8:
        ang_std = float(np.std(np.array(angles, dtype=np.float32)))
        # std 0~45+; map to 0~1
        disp = min(1.0, ang_std / 35.0)
    else:
        disp = 0.0

    # Edge density (too low -> not enough text; too high -> clutter)
    ed = float(np.mean(edges > 0))
    # map to 0~1 where mid-range indicates "texty" scene
    texty = 1.0 - min(1.0, abs(ed - 0.08) / 0.08)

    # Combine: curvature suspicion = mixed edges + angle dispersion, tempered by textiness
    score = 0.55 * mix + 0.35 * disp + 0.10 * texty
    score = float(np.clip(score, 0.0, 1.0))

    return {
        "score": score,
        "features": {
            "mix": mix,
            "dispersion": disp,
            "texty": texty,
            "edge_density": ed,
            "num_lines": int(len(angles)),
        },
        "note": "Higher score => more likely needs non-linear dewarp.",
    }
