"""Image rectification utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import time
import cv2
import numpy as np

from .backends import DoctrBackend, DewarpNetBackend, DocUNetBackend, RectifyResult
from .photometric import (
    EnhanceConfig,
    IlluminationConfig,
    DenoiseConfig,
    correct_illumination,
    denoise,
    apply_photometric_enhance,
)


@dataclass
class RectifyConfig:
    backend: str = "none"  # none | doctr | dewarpnet | docunet
    device: str = "cpu"
    model_dir: Optional[str] = None

    # Photometric pipeline (recommended always ON)
    illumination: IlluminationConfig = IlluminationConfig()
    denoise: DenoiseConfig = DenoiseConfig()
    enhance: EnhanceConfig = EnhanceConfig()


def _get_backend(name: str, device: str, model_dir: Optional[str]):
    name = (name or "none").lower().strip()
    if name == "none":
        return None
    if name == "doctr":
        return DoctrBackend(device=device, model_dir=model_dir)
    if name == "dewarpnet":
        return DewarpNetBackend(device=device, model_dir=model_dir)
    if name == "docunet":
        return DocUNetBackend(device=device, model_dir=model_dir)
    raise ValueError(f"Unknown backend: {name}")


def rectify_image(image_bgr: np.ndarray, cfg: RectifyConfig) -> RectifyResult:
    """
    Pure rectification step:
      - NO text detection
      - Focus on making the entire menu board more OCR-friendly.
    Output is the rectified image coordinate system (for downstream OCR + overlay).
    """
    t0 = time.time()
    meta: Dict[str, Any] = {
        "backend": cfg.backend,
        "device": cfg.device,
        "model_dir": cfg.model_dir,
        "input_shape": [int(image_bgr.shape[0]), int(image_bgr.shape[1])],
        "ops": [],
    }

    out = image_bgr

    # Photometric (pixel-location invariant)
    out, m_illum = correct_illumination(out, cfg.illumination)
    if m_illum.get("illumination"):
        meta["ops"].append(m_illum)

    out, m_den = denoise(out, cfg.denoise)
    if m_den.get("denoise"):
        meta["ops"].append(m_den)

    out, m_enh = apply_photometric_enhance(out, cfg.enhance)
    if m_enh.get("photometric"):
        meta["ops"].append(m_enh)

    # Optional geometric backend (may warp coordinates, which is now allowed in your UI strategy)
    backend = _get_backend(cfg.backend, cfg.device, cfg.model_dir)
    if backend is not None:
        res = backend.rectify(out)
        out = res.image
        meta["ops"].append({"backend_meta": res.meta})

    meta["output_shape"] = [int(out.shape[0]), int(out.shape[1])]
    meta["elapsed_ms"] = int((time.time() - t0) * 1000)
    meta["notes"] = "Overlay and OCR are performed in rectified image coordinate system."

    return RectifyResult(image=out, meta=meta)


def read_image_bgr(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Failed to read image: {path}")
    return img


def write_image_bgr(path: str, image_bgr: np.ndarray) -> None:
    ok = cv2.imwrite(path, image_bgr)
    if not ok:
        raise IOError(f"Failed to write image: {path}")
