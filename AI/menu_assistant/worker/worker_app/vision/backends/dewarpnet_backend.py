from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import cv2

from .base import RectifyBackend, RectifyResult


@dataclass(frozen=True)
class DewarpNetConfig:
    """
    Minimal DewarpNet backend config.

    You can provide:
      - model_dir pointing to a file (.onnx / .pt / .pth) or a directory containing it
    """
    input_size: int = 1024           # typical square resize for dewarp models
    prefer_onnx: bool = True
    strict: bool = False             # if True and model missing => raise
    keep_aspect: bool = True         # letterbox to square

    # Postprocess smoothing/limits can be added later if your model outputs flow/grid.


class DewarpNetBackend(RectifyBackend):
    name = "dewarpnet"

    def __init__(self, device: str = "cpu", model_dir: Optional[str] = None, config: Optional[DewarpNetConfig] = None):
        super().__init__(device=device, model_dir=model_dir)
        self.config = config or DewarpNetConfig()

        self.ready: bool = False
        self.backend: Optional[str] = None  # "onnx" | "torch"
        self.model_path: Optional[Path] = None

        self._ort = None
        self._ort_sess = None
        self._torch = None
        self._torch_model = None

        self._init_meta: Dict[str, Any] = self._lazy_init()

    # -------------------------
    # init
    # -------------------------
    def _find_model(self) -> Optional[Path]:
        if not self.model_dir:
            return None
        p = Path(self.model_dir)
        if p.is_file():
            return p
        if not p.exists():
            return None

        # Prefer ONNX if present
        onnx = sorted(list(p.glob("*.onnx")))
        if onnx:
            return onnx[0]

        # Torch
        pts = sorted(list(p.glob("*.pt")) + list(p.glob("*.pth")))
        if pts:
            return pts[0]
        return None

    def _lazy_init(self) -> Dict[str, Any]:
        meta: Dict[str, Any] = {
            "backend": self.name,
            "device": self.device,
            "model_dir": self.model_dir,
            "ready": False,
            "selected_runtime": None,
            "model_path": None,
            "errors": {},
        }

        self.model_path = self._find_model()
        meta["model_path"] = str(self.model_path) if self.model_path else None

        if self.model_path is None:
            if self.config.strict:
                raise RuntimeError("DewarpNet strict mode: model not found in model_dir.")
            meta["errors"]["model"] = "model not found"
            self.ready = False
            return meta

        suffix = self.model_path.suffix.lower()

        # ONNX first
        if self.config.prefer_onnx and suffix == ".onnx":
            try:
                import onnxruntime as ort  # type: ignore
                self._ort = ort
                providers = ["CPUExecutionProvider"]
                # If you later run on GPU, you can add CUDA provider here conditionally.
                self._ort_sess = ort.InferenceSession(str(self.model_path), providers=providers)
                self.backend = "onnx"
                self.ready = True
                meta["selected_runtime"] = "onnxruntime"
                meta["ready"] = True
                return meta
            except Exception as e:
                meta["errors"]["onnxruntime"] = repr(e)

        # Torch fallback
        if suffix in (".pt", ".pth") or not self.config.prefer_onnx:
            try:
                import torch  # type: ignore
                self._torch = torch
                # NOTE: We don't know your exact model class.
                # This is a placeholder loader that expects TorchScript (.pt) or state_dict with a known class.
                if suffix == ".pt":
                    self._torch_model = torch.jit.load(str(self.model_path), map_location=self.device)
                    self._torch_model.eval()
                    self.backend = "torchscript"
                    self.ready = True
                    meta["selected_runtime"] = "torchscript"
                    meta["ready"] = True
                    return meta
                else:
                    # .pth needs a model class; keep not-ready until you wire the architecture.
                    meta["errors"]["torch"] = "pth provided but model architecture not wired (need model class)."
            except Exception as e:
                meta["errors"]["torch_import_or_load"] = repr(e)

        self.ready = False
        return meta

    # -------------------------
    # preprocess helpers
    # -------------------------
    def _letterbox_to_square(self, img: np.ndarray, size: int) -> Tuple[np.ndarray, Dict[str, Any]]:
        h, w = img.shape[:2]
        scale = size / max(h, w)
        nh, nw = int(round(h * scale)), int(round(w * scale))
        resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)

        canvas = np.zeros((size, size, 3), dtype=resized.dtype)
        top = (size - nh) // 2
        left = (size - nw) // 2
        canvas[top:top + nh, left:left + nw] = resized

        meta = {"scale": scale, "top": top, "left": left, "new_hw": [nh, nw], "orig_hw": [h, w]}
        return canvas, meta

    def _to_float_tensor_nchw(self, img_bgr: np.ndarray) -> np.ndarray:
        # BGR -> RGB, normalize 0..1, NCHW float32
        rgb = img_bgr[:, :, ::-1].astype(np.float32) / 255.0
        chw = np.transpose(rgb, (2, 0, 1))
        return np.expand_dims(chw, axis=0)

    def _from_float_tensor_nchw(self, t: np.ndarray) -> np.ndarray:
        # NCHW RGB -> HWC BGR uint8
        if t.ndim == 4:
            t = t[0]
        rgb = np.transpose(t, (1, 2, 0))
        rgb = np.clip(rgb, 0.0, 1.0)
        bgr = (rgb[:, :, ::-1] * 255.0).astype(np.uint8)
        return bgr

    # -------------------------
    # inference (best-effort)
    # -------------------------
    def rectify(self, image_bgr: np.ndarray) -> RectifyResult:
        meta: Dict[str, Any] = {
            "backend": self.name,
            "device": self.device,
            "model_dir": self.model_dir,
            "init": self._init_meta,
            "ready": self.ready,
            "applied": False,
            "method": None,
        }

        if not self.ready:
            meta["warning"] = "DewarpNet not ready (no model/runtime). Passthrough."
            return RectifyResult(image=image_bgr, meta=meta)

        # preprocess
        inp = image_bgr
        lb_meta = None
        if self.config.keep_aspect:
            inp, lb_meta = self._letterbox_to_square(inp, self.config.input_size)
        else:
            inp = cv2.resize(inp, (self.config.input_size, self.config.input_size), interpolation=cv2.INTER_AREA)

        x = self._to_float_tensor_nchw(inp)

        # ONNX path: assume model outputs an image-like tensor in NCHW, range 0..1
        if self.backend == "onnx":
            try:
                assert self._ort_sess is not None
                input_name = self._ort_sess.get_inputs()[0].name
                out = self._ort_sess.run(None, {input_name: x})
                y = out[0]
                out_bgr = self._from_float_tensor_nchw(y)

                # undo letterbox: crop back to resized region then scale back to orig
                if lb_meta is not None:
                    top, left = lb_meta["top"], lb_meta["left"]
                    nh, nw = lb_meta["new_hw"]
                    cropped = out_bgr[top:top + nh, left:left + nw]
                    oh, ow = lb_meta["orig_hw"]
                    out_bgr = cv2.resize(cropped, (ow, oh), interpolation=cv2.INTER_CUBIC)

                meta["applied"] = True
                meta["method"] = "onnx_image2image"
                meta["preprocess"] = {"letterbox": lb_meta, "input_size": self.config.input_size}
                meta["output_shape"] = [int(out_bgr.shape[0]), int(out_bgr.shape[1])]
                return RectifyResult(image=out_bgr, meta=meta)
            except Exception as e:
                meta["error"] = repr(e)
                meta["warning"] = "ONNX inference failed; passthrough."
                return RectifyResult(image=image_bgr, meta=meta)

        # TorchScript path: assume it outputs NCHW image 0..1
        if self.backend == "torchscript":
            try:
                assert self._torch is not None and self._torch_model is not None
                with self._torch.no_grad():
                    xt = self._torch.from_numpy(x).to(self.device)
                    yt = self._torch_model(xt)
                    y = yt.detach().cpu().numpy()
                out_bgr = self._from_float_tensor_nchw(y)

                if lb_meta is not None:
                    top, left = lb_meta["top"], lb_meta["left"]
                    nh, nw = lb_meta["new_hw"]
                    cropped = out_bgr[top:top + nh, left:left + nw]
                    oh, ow = lb_meta["orig_hw"]
                    out_bgr = cv2.resize(cropped, (ow, oh), interpolation=cv2.INTER_CUBIC)

                meta["applied"] = True
                meta["method"] = "torchscript_image2image"
                meta["preprocess"] = {"letterbox": lb_meta, "input_size": self.config.input_size}
                meta["output_shape"] = [int(out_bgr.shape[0]), int(out_bgr.shape[1])]
                return RectifyResult(image=out_bgr, meta=meta)
            except Exception as e:
                meta["error"] = repr(e)
                meta["warning"] = "TorchScript inference failed; passthrough."
                return RectifyResult(image=image_bgr, meta=meta)

        meta["warning"] = "Unknown dewarp runtime; passthrough."
        return RectifyResult(image=image_bgr, meta=meta)
