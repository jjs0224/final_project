from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

import cv2
import numpy as np

from .base import RectifyBackend, RectifyResult
from .doc_geometry import PerspectiveRectifyParams, find_document_quad, warp_perspective


@dataclass(frozen=True)
class DocUNetConfig:
    """
    Working menu-board rectification backend.

    Pipeline:
      1) (Optional) DocTR orientation predictor
      2) Apply inverse rotation (correction) to make upright
      3) OpenCV contour-based quad detection
      4) Perspective warp to fronto-parallel rectangle

    Controls:
      - min_orientation_confidence: confidence below this => treat as uncertain
      - prefer_fallback_when_low_conf: if uncertain, prefer heuristic/candidate selection
      - try_both_directions_when_uncertain: test 90/270 candidates and pick best by quad-detection quality
    """
    params: PerspectiveRectifyParams = PerspectiveRectifyParams()
    strict_weights: bool = False
    #enable_orientation: DocTR로 회전 추정을 할지 여부
    enable_orientation: bool = True
    #predictor가 낸 confidence가 이 값 미만이면 “불확실”로 판단
    min_orientation_confidence: float = 0.95
    prefer_fallback_when_low_conf: bool = True
    #불확실한 경우 90/270 등 여러 후보를 실제로 돌려보고 최선 선택
    try_both_directions_when_uncertain: bool = True
    prefer_doctr_when_tie: bool = True
    tie_area_ratio: float = 0.01  # 1% 이내면 동률로 간주


class DocUNetBackend(RectifyBackend):
    """
    docunet backend: DocTR orientation (optional) + OpenCV perspective rectify.

    Key decisions:
      - The predictor output is interpreted as "current document orientation".
        Therefore we apply the inverse rotation as the correction:
          correction_angle = (-pred_angle) % 360

      - If confidence is low or parsing fails, we fall back to heuristic candidate rotations
        and select the best one by document quad detection quality.
    """

    name = "docunet"

    def __init__(self, device: str = "cpu", model_dir: Optional[str] = None, config: Optional[DocUNetConfig] = None):
        super().__init__(device=device, model_dir=model_dir)
        self.config = config or DocUNetConfig()

        # torch (future DL weights path)
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

        # doctr (orientation)
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

        self._models_ready: bool = False

    # -------------------------
    # basic helpers
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
    # doctr output normalization/parsing
    # -------------------------
    @staticmethod
    def _normalize_angle(val: Any) -> Optional[int]:
        """
        Normalize angle-like values into one of {0, 90, 180, 270}.
        Supports negative angles: -90 -> 270.
        """
        if val is None:
            return None

        if isinstance(val, (int, np.integer, float, np.floating)):
            v = int(round(float(val)))
            v = v % 360
            return v if v in (0, 90, 180, 270) else None

        if isinstance(val, str):
            s = val.strip().lower()
            mapping = {
                "0": 0, "90": 90, "180": 180, "270": 270,
                "-90": 270,
                "upright": 0, "rot90": 90, "rot180": 180, "rot270": 270,
            }
            if s in mapping:
                return mapping[s]
            for key in ("0", "90", "180", "270", "-90"):
                if key in s:
                    return mapping.get(key, None)

        return None

    @staticmethod
    def _angle_from_doctr_output(out: Any) -> Optional[int]:
        """
        Extract normalized angle in {0,90,180,270} from various doctr outputs.

        Known page_orientation_predictor format (observed):
          [[class_id], [angle_deg], [confidence]]
          e.g. [[1], [-90], [0.9]]
        """
        # dict with angle key
        if isinstance(out, dict):
            for k in ("angle", "orientation", "rotation"):
                if k in out:
                    return DocUNetBackend._normalize_angle(out[k])

        # page_orientation_predictor observed output: [[cls], [angle], [conf]]
        if isinstance(out, (list, tuple)) and len(out) == 3:
            try:
                angle_part = out[1]
                if isinstance(angle_part, (list, tuple, np.ndarray)) and len(angle_part) > 0:
                    angle_part = angle_part[0]
                ang = DocUNetBackend._normalize_angle(angle_part)
                if ang is not None:
                    return ang
            except Exception:
                pass

        # batch list/tuple: try first element recursively
        if isinstance(out, (list, tuple)) and len(out) > 0:
            first = out[0]
            ang = DocUNetBackend._angle_from_doctr_output(first)
            if ang is not None:
                return ang

            # probability vector [p0,p90,p180,p270]
            if len(out) == 4 and all(isinstance(x, (int, float, np.floating, np.integer)) for x in out):
                arr = np.array(out, dtype=float)
                idx = int(arr.argmax())
                return [0, 90, 180, 270][idx]

        # numpy array probability vector
        if isinstance(out, np.ndarray):
            arr = out
            if arr.ndim == 2 and arr.shape[0] == 1:
                arr = arr[0]
            if arr.ndim == 1 and arr.shape[0] == 4:
                idx = int(np.argmax(arr))
                return [0, 90, 180, 270][idx]

        return DocUNetBackend._normalize_angle(out)

    @staticmethod
    def _confidence_from_doctr_output(out: Any) -> Optional[float]:
        """
        Extract confidence from page_orientation_predictor output:
          [[class_id], [angle_deg], [confidence]]
        """
        if isinstance(out, (list, tuple)) and len(out) == 3:
            try:
                conf_part = out[2]
                if isinstance(conf_part, (list, tuple, np.ndarray)) and len(conf_part) > 0:
                    conf_part = conf_part[0]
                return float(conf_part)
            except Exception:
                return None
        return None

    # -------------------------
    # weights discovery (future DL path)
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
    # lazy init (doctr predictor)
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
    # orientation correction (confidence + candidate selection)
    # -------------------------
    def _maybe_apply_orientation(self, image_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Orientation correction with:
          - doctr prediction parsing (angle + confidence)
          - confidence thresholding
          - SAFE fallback: never rotate if all candidates fail to produce a valid document quad
          - candidate testing (prefer 0-degree first for safety)
          - ✅ tie-break: if 0 vs doctr_inverse are nearly equal, prefer doctr_inverse
        """
        meta: Dict[str, Any] = {
            "enabled": bool(self.config.enable_orientation),
            "applied": False,
            "predictor_available": self._orientation_predictor is not None,
        }

        if not self.config.enable_orientation:
            meta["reason"] = "orientation disabled"
            return image_bgr, meta

        if self._orientation_predictor is None:
            meta["reason"] = "orientation predictor unavailable"
            return image_bgr, meta

        # --- helper: score a rotated image by document quad detection quality ---
        def score_rotation(img: np.ndarray) -> Tuple[float, Dict[str, Any]]:
            quad, find_meta = find_document_quad(img, self.config.params)
            if quad is None:
                return 0.0, {"found": False, "find": find_meta}
            best_area = float(find_meta.get("best_area", 0.0))
            # Found quad => big base score, then tie-break by area
            return 1e9 + best_area, {"found": True, "find": find_meta}

        try:
            # 1) run doctr predictor
            rgb = self._bgr_to_rgb(image_bgr)
            pred_out = self._orientation_predictor([rgb])

            meta["raw_output_type"] = type(pred_out).__name__
            try:
                meta["raw_output_preview"] = str(pred_out)[:500]
            except Exception:
                meta["raw_output_preview"] = "<unserializable>"

            pred_angle = self._angle_from_doctr_output(pred_out)  # 0/90/180/270 or None
            pred_conf = self._confidence_from_doctr_output(pred_out)  # float or None

            meta["angle"] = pred_angle
            meta["confidence"] = pred_conf

            # 2) determine uncertainty
            uncertain = False
            if pred_angle is None:
                uncertain = True
                meta["uncertain_reason"] = "angle_parse_failed"
            elif pred_conf is not None and pred_conf < float(self.config.min_orientation_confidence):
                uncertain = True
                meta["uncertain_reason"] = f"low_confidence<{self.config.min_orientation_confidence}"

            # 3) confident path: apply doctr inverse correction directly
            if (not uncertain) and pred_angle in (0, 90, 180, 270):
                correction = (-int(pred_angle)) % 360
                rotated = self._apply_rotation_bgr(image_bgr, correction)

                meta["correction_angle"] = correction
                meta["applied"] = (correction != 0)
                meta["reason"] = "used_doctr_inverse_confident"
                return rotated, meta

            # 4) uncertain path: build candidates
            h, w = image_bgr.shape[:2]
            candidates: List[Tuple[int, str]] = []

            # Always include 0-degree first for safety
            candidates.append((0, "no_rotation"))

            # If landscape, try 90/270
            if w > h:
                candidates.append((90, "fallback_rotate90_w>h"))
                candidates.append((270, "fallback_rotate270_w>h"))

            # Include doctr inverse correction as candidate if available
            doctr_correction: Optional[int] = None
            if pred_angle in (0, 90, 180, 270):
                doctr_correction = (-int(pred_angle)) % 360
                candidates.append((doctr_correction, "doctr_inverse_candidate"))

            # de-duplicate by angle (keep first tag)
            seen = set()
            uniq: List[Tuple[int, str]] = []
            for ang, tag in candidates:
                if ang not in seen:
                    seen.add(ang)
                    uniq.append((ang, tag))
            candidates = uniq

            # If not trying both directions, pick first (safe 0deg)
            if not bool(self.config.try_both_directions_when_uncertain):
                ang, tag = candidates[0]
                rotated = self._apply_rotation_bgr(image_bgr, ang)
                meta["fallback"] = {
                    "applied": False,
                    "chosen": {"angle": ang, "tag": tag},
                    "candidates": candidates,
                    "note": "try_both_directions_when_uncertain is False; chose first candidate (safe 0deg).",
                }
                meta["correction_angle"] = ang
                meta["applied"] = False
                meta["reason"] = "fallback_disabled_try_both_false"
                return rotated, meta

            # 5) score candidates
            best_score = -1.0
            best_ang = 0
            best_tag = "no_rotation"
            best_detail: Dict[str, Any] = {}

            all_failed = True
            scored: List[Dict[str, Any]] = []

            for ang, tag in candidates:
                rotated = self._apply_rotation_bgr(image_bgr, ang)
                s, detail = score_rotation(rotated)

                found = bool(detail.get("found", False))
                if found:
                    all_failed = False

                scored.append({
                    "angle": ang,
                    "tag": tag,
                    "score": s,
                    "found": found,
                    "best_area": float(detail.get("find", {}).get("best_area", 0.0)),
                })

                if s > best_score:
                    best_score = s
                    best_ang = ang
                    best_tag = tag
                    best_detail = detail

            # ✅ SAFETY RULE: if all candidates fail to find quad -> DO NOT ROTATE
            if all_failed or best_score <= 0.0:
                meta["fallback"] = {
                    "applied": False,
                    "chosen": {"angle": 0, "tag": "no_rotation_all_candidates_failed"},
                    "candidates": candidates,
                    "scored": scored,
                    "scoring": {"all_failed": True},
                }
                meta["correction_angle"] = 0
                meta["applied"] = False
                meta["reason"] = "fallback_disabled_all_candidates_failed"
                return image_bgr, meta

            # ✅ TIE-BREAK: if 0deg and doctr_inverse are both found and areas are nearly equal, prefer doctr_inverse
            if bool(self.config.prefer_doctr_when_tie) and (doctr_correction is not None):
                areas = {s["angle"]: float(s.get("best_area", 0.0)) for s in scored if s.get("found", False)}
                if 0 in areas and doctr_correction in areas:
                    a0 = areas[0]
                    ad = areas[doctr_correction]
                    denom = max(a0, ad, 1e-6)
                    rel_diff = abs(a0 - ad) / denom

                    # if difference within tie ratio, trust doctr prior
                    if rel_diff <= float(self.config.tie_area_ratio):
                        best_ang = doctr_correction
                        best_tag = "doctr_inverse_tie_break"
                        best_detail = {
                            "tie_break": {
                                "rel_diff": rel_diff,
                                "area_0deg": a0,
                                "area_doctr_inverse": ad,
                                "tie_area_ratio": float(self.config.tie_area_ratio),
                            }
                        }

            # apply best rotation
            rotated = self._apply_rotation_bgr(image_bgr, best_ang)
            meta["fallback"] = {
                "applied": best_ang != 0,
                "chosen": {"angle": best_ang, "tag": best_tag},
                "candidates": candidates,
                "scored": scored,
                "scoring": best_detail,
            }
            meta["correction_angle"] = best_ang
            meta["applied"] = (best_ang != 0)
            meta["reason"] = "used_fallback_candidate_selection_safe"
            return rotated, meta

        except Exception as e:
            meta["error"] = repr(e)
            meta["reason"] = "orientation inference failed"
            return image_bgr, meta

    # -------------------------
    # public
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

        # 1) orientation correction
        oriented, orient_meta = self._maybe_apply_orientation(image_bgr)
        meta["orientation"] = orient_meta

        # 2) perspective rectify on oriented image
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
