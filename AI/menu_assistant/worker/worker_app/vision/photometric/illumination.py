from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any
import cv2
import numpy as np


@dataclass
class IlluminationConfig:
    enable: bool = True
    # large-kernel background estimation for shadow correction
    blur_ksize: int = 51
    strength: float = 0.85  # 0~1; higher => more correction


def correct_illumination(image_bgr: np.ndarray, cfg: IlluminationConfig) -> tuple[np.ndarray, Dict[str, Any]]:
    """
    Simple, robust illumination correction without text detection.
    Works reasonably on shadow/uneven lighting; does not move pixels.
    """
    meta: Dict[str, Any] = {"illumination": []}
    if not cfg.enable:
        return image_bgr, meta

    out = image_bgr.copy()
    k = int(cfg.blur_ksize)
    if k % 2 == 0:
        k += 1

    # Estimate background illumination on grayscale
    gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
    bg = cv2.GaussianBlur(gray, (k, k), 0)

    # Avoid division by zero
    bg = np.clip(bg.astype(np.float32), 1.0, 255.0)
    gray_f = gray.astype(np.float32)

    # Normalize and blend
    norm = (gray_f / bg) * 128.0
    norm = np.clip(norm, 0, 255).astype(np.uint8)

    # Apply correction by adjusting V channel in HSV
    hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    v2 = cv2.addWeighted(v, 1.0 - cfg.strength, norm, cfg.strength, 0)
    hsv2 = cv2.merge([h, s, v2])
    out2 = cv2.cvtColor(hsv2, cv2.COLOR_HSV2BGR)

    meta["illumination"].append({"op": "shadow_correction", "blur_ksize": k, "strength": cfg.strength})
    return out2, meta
