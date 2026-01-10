from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any
import cv2
import numpy as np


@dataclass
class DenoiseConfig:
    enable: bool = True
    h: int = 8
    hColor: int = 8
    templateWindowSize: int = 7
    searchWindowSize: int = 21


def denoise(image_bgr: np.ndarray, cfg: DenoiseConfig) -> tuple[np.ndarray, Dict[str, Any]]:
    meta: Dict[str, Any] = {"denoise": []}
    if not cfg.enable:
        return image_bgr, meta

    out = cv2.fastNlMeansDenoisingColored(
        image_bgr,
        None,
        h=cfg.h,
        hColor=cfg.hColor,
        templateWindowSize=cfg.templateWindowSize,
        searchWindowSize=cfg.searchWindowSize,
    )
    meta["denoise"].append(
        {
            "op": "fastNlMeansDenoisingColored",
            "h": cfg.h,
            "hColor": cfg.hColor,
            "templateWindowSize": cfg.templateWindowSize,
            "searchWindowSize": cfg.searchWindowSize,
        }
    )
    return out, meta
