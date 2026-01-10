from __future__ import annotations

from typing import Any, Dict, Optional
import numpy as np

from .base import RectifyBackend, RectifyResult


class DoctrBackend(RectifyBackend):
    name = "doctr"

    def __init__(self, device: str = "cpu", model_dir: Optional[str] = None):
        super().__init__(device=device, model_dir=model_dir)

        # Lazy import to avoid hard dependency
        try:
            import doctr  # noqa: F401
        except Exception as e:
            self._import_error = e
        else:
            self._import_error = None

    def rectify(self, image_bgr: np.ndarray) -> RectifyResult:
        if self._import_error is not None:
            raise RuntimeError(
                "DocTR backend requested, but doctr is not installed/available. "
                "Install DocTR and required deps, or use backend='none'. "
                f"Original error: {self._import_error}"
            )

        # Placeholder: implement GeoTr/IllTr based rectification here.
        # For now, passthrough.
        meta: Dict[str, Any] = {
            "backend": self.name,
            "device": self.device,
            "model_dir": self.model_dir,
            "warning": "DoctrBackend is a placeholder (passthrough). Implement inference.",
        }
        return RectifyResult(image=image_bgr, meta=meta)
