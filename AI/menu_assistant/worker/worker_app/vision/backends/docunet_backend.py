from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

from .base import RectifyBackend, RectifyResult
from .doc_geometry import PerspectiveRectifyParams, find_document_quad, warp_perspective


@dataclass(frozen=True)
class DocUNetConfig:
    """
    Operational config for 'docunet' backend.

    This backend provides a working menu-board rectification even without deep learning weights,
    by using robust OpenCV contour-based perspective correction.

    If you later wire a real DocUNet model (torch weights) you can:
      - keep the same interface
      - run DL inference first
      - fallback to perspective correction if DL fails

    params: PerspectiveRectifyParams controlling contour/warp behavior
    strict_weights: if True, raise when weights are missing; if False, fallback to OpenCV.
    """
    params: PerspectiveRectifyParams = PerspectiveRectifyParams()
    strict_weights: bool = False


class DocUNetBackend(RectifyBackend):
    """
    DocUNet backend - pipeline friendly implementation.

    Compatible with:
      rectify.py -> _get_backend("docunet", device, model_dir) -> DocUNetBackend(device, model_dir)
      rectify.py -> backend.rectify(image_bgr) -> RectifyResult(image=<BGR>, meta=<dict>)

    Behavior:
      - If torch+weights are wired (optional), you can run DL-based dewarp later.
      - Regardless, this version works today for menu boards via:
            detect largest quadrilateral -> perspective warp -> return rectified image.

    model_dir handling:
      - If model_dir points to a directory, this backend will optionally look for weights there.
      - For the OpenCV path, model_dir is not required.
    """

    name = "docunet"

    def __init__(self, device: str = "cpu", model_dir: Optional[str] = None, config: Optional[DocUNetConfig] = None):
        super().__init__(device=device, model_dir=model_dir)
        self.config = config or DocUNetConfig()

        # Optional torch wiring (future extension)
        self._torch = None
        self._torch_import_error: Optional[BaseException] = None

        self._model = None
        self._weights_path: Optional[Path] = None
        self._models_ready: bool = False

        try:
            import torch as _torch  # type: ignore
        except Exception as e:
            self._torch_import_error = e
            self._torch = None
        else:
            self._torch = _torch
            self._torch_import_error = None

    @staticmethod
    def _validate_image(image_bgr: np.ndarray) -> Tuple[int, int]:
        if not isinstance(image_bgr, np.ndarray):
            raise TypeError(f"image_bgr must be np.ndarray, got {type(image_bgr)}")
        if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
            raise ValueError(f"image_bgr must have shape (H, W, 3). Got {image_bgr.shape}")
        h, w = int(image_bgr.shape[0]), int(image_bgr.shape[1])
        if h < 2 or w < 2:
            raise ValueError(f"image_bgr too small: {(h, w)}")
        return h, w

    def _resolve_weights_path(self) -> Optional[Path]:
        if not self.model_dir:
            return None
        p = Path(self.model_dir)
        if p.is_file():
            return p
        if not p.exists():
            return None
        candidates = [
            p / "docunet.pth",
            p / "docunet.pt",
            p / "best.pth",
            p / "model.pth",
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                return c
        found = sorted(list(p.glob("*.pth")) + list(p.glob("*.pt")))
        return found[0] if found else None

    def _lazy_init_models(self) -> Dict[str, Any]:
        if self._models_ready:
            return {
                "models_ready": self._model is not None,
                "init": "cached",
                "weights_path": str(self._weights_path) if self._weights_path else None,
                "torch_available": self._torch is not None,
            }

        self._weights_path = self._resolve_weights_path()
        self._models_ready = True

        return {
            "models_ready": False,  # DL model not wired by default
            "init": "opencv_fallback_ready",
            "weights_path": str(self._weights_path) if self._weights_path else None,
            "torch_available": self._torch is not None,
            "torch_import_error": repr(self._torch_import_error) if self._torch_import_error else None,
        }

    def rectify(self, image_bgr: np.ndarray) -> RectifyResult:
        h, w = self._validate_image(image_bgr)
        init_meta = self._lazy_init_models()

        meta: Dict[str, Any] = {
            "backend": self.name,
            "device": self.device,
            "model_dir": self.model_dir,
            "input_shape": [h, w],
            "init": init_meta,
            "applied": False,
            "method": "opencv_perspective",
            "opencv": {
                "params": {
                    "canny1": self.config.params.canny1,
                    "canny2": self.config.params.canny2,
                    "dilate_iter": self.config.params.dilate_iter,
                    "approx_eps_ratio": self.config.params.approx_eps_ratio,
                    "min_area_ratio": self.config.params.min_area_ratio,
                    "border": self.config.params.border,
                }
            },
        }

        if self.config.strict_weights and self._weights_path is None:
            raise RuntimeError(
                "DocUNet strict mode: weights were not found. "
                "Provide --model_dir pointing to a weights file or directory."
            )

        quad, find_meta = find_document_quad(image_bgr, self.config.params)
        meta["opencv"]["find"] = find_meta

        if quad is None:
            meta["warning"] = "No document-like quadrilateral found; passthrough."
            meta["output_shape"] = [h, w]
            return RectifyResult(image=image_bgr, meta=meta)

        try:
            warped, warp_meta = warp_perspective(image_bgr, quad, self.config.params)
            meta["opencv"]["warp"] = warp_meta
            meta["applied"] = True
            meta["output_shape"] = [int(warped.shape[0]), int(warped.shape[1])]
            return RectifyResult(image=warped, meta=meta)
        except Exception as e:
            meta["warning"] = "Perspective warp failed; passthrough."
            meta["error"] = repr(e)
            meta["output_shape"] = [h, w]
            return RectifyResult(image=image_bgr, meta=meta)
