from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any
import cv2
import numpy as np


@dataclass
class EnhanceConfig:
    apply_clahe: bool = True
    clahe_clip_limit: float = 2.0
    clahe_tile_grid_size: int = 8

    apply_gamma: bool = True
    gamma: float = 1.15  # >1 slightly brightens midtones

    apply_unsharp: bool = True
    unsharp_amount: float = 1.2
    unsharp_sigma: float = 1.0


def _apply_gamma(image_bgr: np.ndarray, gamma: float) -> np.ndarray:
    if gamma <= 0:
        return image_bgr
    inv = 1.0 / gamma
    table = np.array([(i / 255.0) ** inv * 255 for i in range(256)]).astype("uint8")
    return cv2.LUT(image_bgr, table)


def apply_photometric_enhance(image_bgr: np.ndarray, cfg: EnhanceConfig) -> tuple[np.ndarray, Dict[str, Any]]:
    meta: Dict[str, Any] = {"photometric": []}
    out = image_bgr.copy()

    # CLAHE on L channel
    if cfg.apply_clahe:
        lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(
            clipLimit=float(cfg.clahe_clip_limit),
            tileGridSize=(int(cfg.clahe_tile_grid_size), int(cfg.clahe_tile_grid_size)),
        )
        l2 = clahe.apply(l)
        lab2 = cv2.merge([l2, a, b])
        out = cv2.cvtColor(lab2, cv2.COLOR_LAB2BGR)
        meta["photometric"].append({"op": "clahe", "clip_limit": cfg.clahe_clip_limit, "tile": cfg.clahe_tile_grid_size})

    if cfg.apply_gamma:
        out = _apply_gamma(out, cfg.gamma)
        meta["photometric"].append({"op": "gamma", "gamma": cfg.gamma})

    if cfg.apply_unsharp:
        blurred = cv2.GaussianBlur(out, (0, 0), cfg.unsharp_sigma)
        out = cv2.addWeighted(out, 1.0 + cfg.unsharp_amount, blurred, -cfg.unsharp_amount, 0)
        meta["photometric"].append({"op": "unsharp", "amount": cfg.unsharp_amount, "sigma": cfg.unsharp_sigma})

    return out, meta
