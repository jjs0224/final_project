from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

from .base import RectifyBackend, RectifyResult
from .doc_geometry import PerspectiveRectifyParams, find_document_quad, warp_perspective


@dataclass(frozen=True)
class DocUNetConfig:
    """
    Working menu-board rectification backend.

    - enable_orientation: try DocTR orientation (0/90/180/270) BEFORE perspective warp
    - strict_weights: reserved for future DL weights; if True and weights missing -> raise
    - params: OpenCV perspective detection/warp parameters
    """
    params: PerspectiveRectifyParams = PerspectiveRectifyParams()
    strict_weights: bool = False
    enable_orientation: bool = True


class DocUNetBackend(RectifyBackend):
    """
    docunet backend = (optional) DocTR orientation + OpenCV perspective rectification.

    IMPORTANT:
    - This class MUST override rectify(). If you see NotImplementedError from base.py,
      it usually means this file's indentation/structure got corrupted.
    """

    name = "docunet"

    def __init__(self, device: str = "cpu", model_dir: Optional[str] = None, config: Optional[DocUNetConfig] = None):
        super().__init__(device=device, model_dir=model_dir)
        self.config = config or DocUNetConfig()

        # Optional torch wiring (future DL path)
        self._torch = None
        self._torch_import_error: Optional[BaseException] = None
        self._model = None
        self._weights_path: Optional[Path] = None

        try:
            import torch as _torch  # type: ignore
        except Exception as e:
            self._torch = None
            self._torch_import_error = e
        else:
            self._torch = _torch
            self._torch_import_error = None

        # Optional doctr wiring for orientation
        self._doctr = None
        self._doctr_import_error: Optional[BaseException] = None
        self._orientation_predictor = None

        try:
            import doctr as _doctr  # type: ignore
        except Exception as e:
            self._doctr = None
            self._doctr_import_error = e
        else:
            self._doctr = _doctr
            self._doctr_import_error = None

        self._models_ready: bool = False  # lazy init flag

    # -------------------------
    # Validation / helpers
    # -------------------------
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

    @staticmethod
    def _bgr_to_rgb(image_bgr: np.ndarray) -> np.ndarray:
        return image_bgr[:, :, ::-1].copy()

    @staticmethod
    def _normalize_angle(val: Any) -> Optional[int]:
        if val is None:
            return None
        if isinstance(val, (int, np.integer, float, np.floating)):
            v = int(round(float(val)))
            v = v % 360  # -90 -> 270 으로 변환
            return v if v in (0, 90, 180, 270) else None
        if isinstance(val, (float, np.floating)):
            v = int(round(float(val)))
            return v % 360 if v % 90 == 0 else None
        if isinstance(val, str):
            s = val.strip().lower()
            mapping = {
                "0": 0, "90": 90, "180": 180, "270": 270,
                "upright": 0, "rot90": 90, "rot180": 180, "rot270": 270,
            }
            if s in mapping:
                return mapping[s]
            for key in ("0", "90", "180", "270"):
                if key in s:
                    return int(key)
        return None

    @staticmethod
    def _angle_from_doctr_output(out: Any) -> Optional[int]:
        if isinstance(out, dict):
            for k in ("angle", "orientation", "rotation"):
                if k in out:
                    return DocUNetBackend._normalize_angle(out[k])

        if isinstance(out, (list, tuple)) and len(out) > 0:
            first = out[0]
            ang = DocUNetBackend._angle_from_doctr_output(first)
            if ang is not None:
                return ang
            if len(out) == 4 and all(isinstance(x, (int, float, np.floating, np.integer)) for x in out):
                arr = np.array(out, dtype=float)
                return [0, 90, 180, 270][int(arr.argmax())]

        if isinstance(out, np.ndarray):
            arr = out
            if arr.ndim == 2 and arr.shape[0] == 1:
                arr = arr[0]
            if arr.ndim == 1 and arr.shape[0] == 4:
                return [0, 90, 180, 270][int(np.argmax(arr))]
        if isinstance(out, (list, tuple)) and len(out) == 3:
            # page_orientation_predictor output like: [[class_id], [angle_deg], [confidence]]
            try:
                angle_candidate = out[1][0] if isinstance(out[1], (list, tuple, np.ndarray)) else out[1]
                return DocUNetBackend._normalize_angle(angle_candidate)
            except Exception:
                pass

        return DocUNetBackend._normalize_angle(out)

    @staticmethod
    def _apply_rotation_bgr(image_bgr: np.ndarray, angle: int) -> np.ndarray:
        a = angle % 360
        if a == 0:
            return image_bgr
        if a == 90:
            return cv2.rotate(image_bgr, cv2.ROTATE_90_CLOCKWISE)
        if a == 180:
            return cv2.rotate(image_bgr, cv2.ROTATE_180)
        if a == 270:
            return cv2.rotate(image_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return image_bgr

    # -------------------------
    # Optional: weights discovery (future DL path)
    # -------------------------
    def _resolve_weights_path(self) -> Optional[Path]:
        if not self.model_dir:
            return None
        p = Path(self.model_dir)
        if p.is_file():
            return p
        if not p.exists():
            return None
        candidates = [p / "docunet.pth", p / "docunet.pt", p / "best.pth", p / "model.pth"]
        for c in candidates:
            if c.exists() and c.is_file():
                return c
        found = sorted(list(p.glob("*.pth")) + list(p.glob("*.pt")))
        return found[0] if found else None

    # -------------------------
    # Lazy init (v2 doctr API support)
    # -------------------------
    def _lazy_init_models(self) -> Dict[str, Any]:
        if self._models_ready:
            return {
                "init": "cached",
                "weights_path": str(self._weights_path) if self._weights_path else None,
                "torch_available": self._torch is not None,
                "doctr_available": self._doctr is not None,
                "orientation_predictor_available": self._orientation_predictor is not None,
            }

        self._weights_path = self._resolve_weights_path()

        init_meta: Dict[str, Any] = {
            "init": "opencv_perspective_ready",
            "weights_path": str(self._weights_path) if self._weights_path else None,
            "torch_available": self._torch is not None,
            "torch_import_error": repr(self._torch_import_error) if self._torch_import_error else None,
            "doctr_available": self._doctr is not None,
            "doctr_import_error": repr(self._doctr_import_error) if self._doctr_import_error else None,
        }

        # Try doctr orientation predictors (version differences)
        if self.config.enable_orientation and self._doctr is not None:
            try:
                from doctr.models import page_orientation_predictor  # type: ignore
                self._orientation_predictor = page_orientation_predictor(pretrained=True)
                init_meta["orientation_predictor_name"] = "page_orientation_predictor"
            except Exception as e1:
                try:
                    from doctr.models import crop_orientation_predictor  # type: ignore
                    self._orientation_predictor = crop_orientation_predictor(pretrained=True)
                    init_meta["orientation_predictor_name"] = "crop_orientation_predictor"
                except Exception as e2:
                    self._orientation_predictor = None
                    init_meta["orientation_predictor_error"] = {
                        "page_orientation_predictor": repr(e1),
                        "crop_orientation_predictor": repr(e2),
                    }

        self._models_ready = True
        init_meta["orientation_predictor_available"] = self._orientation_predictor is not None
        return init_meta

    # -------------------------
    # Orientation -> perspective
    # -------------------------
    def _maybe_apply_orientation(self, image_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        meta: Dict[str, Any] = {
            "enabled": bool(self.config.enable_orientation),
            "applied": False,
            "predictor_available": self._orientation_predictor is not None,
        }

        if not self.config.enable_orientation:
            return image_bgr, meta

        if self._orientation_predictor is None:
            meta["reason"] = "orientation predictor unavailable"
            return image_bgr, meta

        try:
            rgb = self._bgr_to_rgb(image_bgr)
            pred_out = self._orientation_predictor([rgb])
            try:
                meta["raw_output_preview"] = str(pred_out)[:500]
            except Exception:
                meta["raw_output_preview"] = "<unserializable>"
            angle = self._angle_from_doctr_output(pred_out)
            meta["raw_output_type"] = type(pred_out).__name__
            meta["angle"] = angle

            if angle in (0, 90, 180, 270):
                # predictor가 준 값은 '현재 문서 방향'으로 보고, 정상화는 반대 방향으로 회전
                correction = (-int(angle)) % 360
                rotated = self._apply_rotation_bgr(image_bgr, correction)

                meta["angle"] = angle  # 모델이 예측한 '문서 방향'
                meta["correction_angle"] = correction  # 실제 적용한 회전
                meta["applied"] = (correction != 0)
                return rotated, meta
                meta["applied"] = (angle != 0)
                return rotated, meta
            h, w = image_bgr.shape[:2]
            if (angle is None) and (w > h):
                rotated = self._apply_rotation_bgr(image_bgr, 270)  # 필요하면 90으로 변경
                meta["fallback"] = {"applied": True, "rule": "angle_none_and_w>h -> rotate270"}
                meta["angle"] = 270
                meta["applied"] = True
                return rotated, meta
            meta["reason"] = "angle not normalized to 0/90/180/270"
            return image_bgr, meta

        except Exception as e:
            meta["error"] = repr(e)
            meta["reason"] = "orientation inference failed"
            return image_bgr, meta

    # -------------------------
    # PUBLIC: rectify (MUST override)
    # -------------------------
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
            "method": "orientation_then_opencv_perspective",
            "orientation": {},
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

        oriented, orient_meta = self._maybe_apply_orientation(image_bgr)
        meta["orientation"] = orient_meta

        quad, find_meta = find_document_quad(oriented, self.config.params)
        meta["opencv"]["find"] = find_meta

        if quad is None:
            meta["warning"] = "No document-like quadrilateral found; returning oriented image."
            meta["applied"] = bool(orient_meta.get("applied"))
            meta["output_shape"] = [int(oriented.shape[0]), int(oriented.shape[1])]
            return RectifyResult(image=oriented, meta=meta)

        try:
            warped, warp_meta = warp_perspective(oriented, quad, self.config.params)
            meta["opencv"]["warp"] = warp_meta
            meta["applied"] = True
            meta["output_shape"] = [int(warped.shape[0]), int(warped.shape[1])]
            return RectifyResult(image=warped, meta=meta)
        except Exception as e:
            meta["warning"] = "Perspective warp failed; returning oriented image."
            meta["error"] = repr(e)
            meta["applied"] = bool(orient_meta.get("applied"))
            meta["output_shape"] = [int(oriented.shape[0]), int(oriented.shape[1])]
            return RectifyResult(image=oriented, meta=meta)
