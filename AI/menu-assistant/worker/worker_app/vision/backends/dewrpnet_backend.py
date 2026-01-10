from __future__ import annotations

from typing import Any, Dict, Optional
import numpy as np

from .base import RectifyBackend, RectifyResult


class DewarpNetBackend(RectifyBackend):
    name = "dewarpnet"

    def __init__(self, device: str = "cpu", model_dir: Optional[str] = None):
        super().__init__(device=device, model_dir=model_dir)
        self._ready = False
        self._import_error = None

        # You can implement real loading here (PyTorch etc.)
        try:
            import torch  # noqa: F401
        except Exception as e:
            self._import_error = e
        else:
            self._ready = True

    def rectify(self, image_bgr: np.ndarray) -> RectifyResult:
        if not self._ready:
            raise RuntimeError(
                "DewarpNet backend requested, but torch is not installed/available (or model not loaded). "
                "Install deps + weights and implement loading, or use backend='none'. "
                f"Original error: {self._import_error}"
            )

        meta: Dict[str, Any] = {
            "backend": self.name,
            "device": self.device,
            "model_dir": self.model_dir,
            "warning": "DewarpNetBackend is a placeholder (passthrough). Implement inference.",
        }
        return RectifyResult(image=image_bgr, meta=meta)
