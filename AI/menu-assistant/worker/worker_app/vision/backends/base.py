from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import numpy as np


@dataclass
class RectifyResult:
    image: np.ndarray  # BGR uint8
    meta: Dict[str, Any]


class RectifyBackend:
    """
    Backend interface for geometric/illumination rectification.
    Input/Output must be BGR uint8 images to keep OpenCV compatibility.
    """
    name: str = "base"

    def __init__(self, device: str = "cpu", model_dir: Optional[str] = None):
        self.device = device
        self.model_dir = model_dir

    def rectify(self, image_bgr: np.ndarray) -> RectifyResult:
        raise NotImplementedError
