from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from .base import RectifyBackend, RectifyResult


@dataclass(frozen=True)
class DewarpNetConfig:
    """
    DewarpNet backend config aligned to the DewarpNet infer.py you shared:

        --wc_model_path <file>
        --bm_model_path <file>
        --img_path <DIR>
        --out_path <DIR>
        [--show]

    This backend follows the existing pipeline conventions:
      - RectifyBackend(device, model_dir)
      - ready gating (passthrough if not ready, unless strict=True)
      - rich meta logs

    Important fix vs earlier attempt:
      - We ALWAYS pass absolute paths to subprocess to avoid cwd-relative path duplication issues on Windows.
    """
    infer_py: Optional[str] = None
    wc_model_path: Optional[str] = None
    bm_model_path: Optional[str] = None

    python_executable: str = sys.executable
    timeout_sec: int = 240
    strict: bool = False

    temp_root: Optional[str] = None
    keep_debug_files: bool = False
    show: bool = False
    extra_args: Tuple[str, ...] = ()

    cmd_template: Tuple[str, ...] = (
        "{py}",
        "{infer_py}",
        "--wc_model_path", "{wc}",
        "--bm_model_path", "{bm}",
        "--img_path", "{inp_dir}",
        "--out_path", "{out_dir}",
        "{show_flag}",
    )


class DewarpNetBackend(RectifyBackend):
    """
    DewarpNet wc+bm backend using infer.py directory I/O.
    Name kept as "dewarpnet" for compatibility with AutoBackend selection logic.
    """
    name = "dewarpnet"

    def __init__(self, device: str = "cpu", model_dir: Optional[str] = None, config: Optional[DewarpNetConfig] = None):
        super().__init__(device=device, model_dir=model_dir)
        self.config = config or DewarpNetConfig()

        self.ready: bool = False
        self._resolved: Dict[str, Optional[str]] = {"infer_py": None, "wc": None, "bm": None}
        self._init_meta: Dict[str, Any] = self._lazy_init()

    # ----------------------------
    # helpers
    # ----------------------------
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
    def _list_images(dir_path: str) -> List[str]:
        exts = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff")
        out: List[str] = []
        if not os.path.isdir(dir_path):
            return out
        for fn in os.listdir(dir_path):
            if fn.lower().endswith(exts):
                out.append(os.path.join(dir_path, fn))
        out.sort()
        return out

    @staticmethod
    def _first_match(patterns: Tuple[str, ...]) -> Optional[str]:
        for p in patterns:
            hits = sorted(glob.glob(p))
            if hits:
                return hits[0]
        return None

    @staticmethod
    def _to_abs(p: Optional[str]) -> Optional[str]:
        if not p:
            return None
        # Normalize separators and resolve relative paths from current working directory
        return str(Path(p).expanduser().resolve())

    def _discover_from_model_dir(self, model_dir: str) -> Dict[str, Optional[str]]:
        """
        Discover infer.py + wc/bm checkpoints under model_dir.

        Heuristics:
        1) infer.py: in model_dir or common subfolders
        2) wc/bm: prefer filenames containing 'wc'/'bm'
        3) fallback for official DewarpNet final models:
             wc: unetnc_doc3d*.pkl/pth/pt
             bm: dnetccnl_doc3d*.pkl/pth/pt
        """
        out: Dict[str, Optional[str]] = {"infer_py": None, "wc": None, "bm": None}

        infer_candidates = (
            os.path.join(model_dir, "infer.py"),
            os.path.join(model_dir, "tools", "infer.py"),
            os.path.join(model_dir, "scripts", "infer.py"),
            os.path.join(model_dir, "DewarpNet_master", "infer.py"),
            os.path.join(model_dir, "DewarpNet", "infer.py"),
            os.path.join(model_dir, "dewarpnet", "infer.py"),
        )
        for c in infer_candidates:
            if os.path.isfile(c):
                out["infer_py"] = c
                break

        ckpt_exts = ("pth", "pt", "pkl")

        wc = self._first_match(tuple(os.path.join(model_dir, f"*wc*.{ext}") for ext in ckpt_exts) +
                               tuple(os.path.join(model_dir, f"*WC*.{ext}") for ext in ckpt_exts))
        bm = self._first_match(tuple(os.path.join(model_dir, f"*bm*.{ext}") for ext in ckpt_exts) +
                               tuple(os.path.join(model_dir, f"*BM*.{ext}") for ext in ckpt_exts) +
                               tuple(os.path.join(model_dir, f"*bmap*.{ext}") for ext in ckpt_exts) +
                               tuple(os.path.join(model_dir, f"*mapping*.{ext}") for ext in ckpt_exts))

        if wc is None:
            wc = self._first_match(tuple(os.path.join(model_dir, f"unetnc_doc3d*.{ext}") for ext in ckpt_exts) +
                                   tuple(os.path.join(model_dir, f"*unetnc*doc3d*.{ext}") for ext in ckpt_exts))
        if bm is None:
            bm = self._first_match(tuple(os.path.join(model_dir, f"dnetccnl_doc3d*.{ext}") for ext in ckpt_exts) +
                                   tuple(os.path.join(model_dir, f"*dnetccnl*doc3d*.{ext}") for ext in ckpt_exts))

        out["wc"] = wc
        out["bm"] = bm
        return out

    def _lazy_init(self) -> Dict[str, Any]:
        meta: Dict[str, Any] = {
            "backend": self.name,
            "device": self.device,
            "model_dir": self.model_dir,
            "cfg": asdict(self.config),
            "resolved": {},
            "ready": False,
            "errors": {},
        }

        # Resolve model_dir to absolute early (critical on Windows subprocess)
        model_dir_abs = self._to_abs(self.model_dir) if self.model_dir else None

        infer_py = self.config.infer_py
        wc = self.config.wc_model_path
        bm = self.config.bm_model_path

        if model_dir_abs:
            discovered = self._discover_from_model_dir(model_dir_abs)
            infer_py = infer_py or discovered["infer_py"]
            wc = wc or discovered["wc"]
            bm = bm or discovered["bm"]

        # Always convert to absolute paths to avoid cwd-relative duplication
        infer_py = self._to_abs(infer_py)
        wc = self._to_abs(wc)
        bm = self._to_abs(bm)

        self._resolved["infer_py"] = infer_py
        self._resolved["wc"] = wc
        self._resolved["bm"] = bm
        meta["resolved"] = dict(self._resolved)

        if not infer_py or not os.path.isfile(infer_py):
            meta["errors"]["infer_py"] = "infer.py not found. Ensure model_dir points to folder containing infer.py."
        if not wc or not os.path.isfile(wc):
            meta["errors"]["wc_model_path"] = "wc checkpoint not found. Put wc ckpt in model_dir or set config.wc_model_path."
        if not bm or not os.path.isfile(bm):
            meta["errors"]["bm_model_path"] = "bm checkpoint not found. Put bm ckpt in model_dir or set config.bm_model_path."

        self.ready = (len(meta["errors"]) == 0)
        meta["ready"] = self.ready
        meta["model_dir_abs"] = model_dir_abs

        if self.config.strict and not self.ready:
            raise RuntimeError(f"DewarpNet strict mode: not ready.\n{json.dumps(meta, ensure_ascii=False, indent=2)}")

        return meta

    def _build_cmd(self, inp_dir: str, out_dir: str) -> Tuple[str, ...]:
        infer_py = self._resolved["infer_py"]
        wc = self._resolved["wc"]
        bm = self._resolved["bm"]
        assert infer_py and wc and bm, "Backend not ready; cannot build command."

        show_flag = "--show" if self.config.show else ""
        mapping = {
            "py": self.config.python_executable,
            "infer_py": infer_py,  # ABS path
            "wc": wc,              # ABS path
            "bm": bm,              # ABS path
            "inp_dir": inp_dir,    # ABS temp path
            "out_dir": out_dir,    # ABS temp path
            "show_flag": show_flag,
        }
        cmd = [s.format(**mapping) for s in self.config.cmd_template]
        cmd = [c for c in cmd if c.strip() != ""]
        cmd += list(self.config.extra_args)
        return tuple(cmd)

    # ----------------------------
    # main API
    # ----------------------------
    def rectify(self, image_bgr: np.ndarray) -> RectifyResult:
        h, w = self._validate_image(image_bgr)

        meta: Dict[str, Any] = {
            "backend": self.name,
            "device": self.device,
            "model_dir": self.model_dir,
            "init": self._init_meta,
            "ready": self.ready,
            "applied": False,
            "method": "infer_py_dir_io",
            "input_shape": [h, w],
        }

        if not self.ready:
            meta["warning"] = "DewarpNet not ready; passthrough."
            return RectifyResult(image=image_bgr, meta=meta)

        tmp_root = self.config.temp_root or tempfile.gettempdir()
        workdir = tempfile.mkdtemp(prefix="dewarpnet_", dir=tmp_root)
        inp_dir = os.path.join(workdir, "inp")
        out_dir = os.path.join(workdir, "out")
        os.makedirs(inp_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        # Put exactly one image; DewarpNet infer.py loops over directory contents.
        fname = "input.png"
        inp_img_path = os.path.join(inp_dir, fname)

        try:
            if not cv2.imwrite(inp_img_path, image_bgr):
                raise RuntimeError(f"cv2.imwrite failed: {inp_img_path}")

            cmd = self._build_cmd(inp_dir=inp_dir, out_dir=out_dir)
            meta["cmd"] = list(cmd)

            t0 = time.time()
            # IMPORTANT: do not set cwd to infer.py directory; absolute paths are used anyway.
            proc = subprocess.run(
                cmd,
                cwd=None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.config.timeout_sec,
                check=False,
                text=True,
            )
            meta["subprocess"] = {
                "returncode": proc.returncode,
                "elapsed_ms": int((time.time() - t0) * 1000),
                "stdout_tail": (proc.stdout[-2000:] if proc.stdout else ""),
                "stderr_tail": (proc.stderr[-2000:] if proc.stderr else ""),
            }

            if proc.returncode != 0:
                raise RuntimeError(f"infer.py failed (returncode={proc.returncode})")

            expected = os.path.join(out_dir, fname)
            out_path: Optional[str] = expected if os.path.isfile(expected) else None

            if out_path is None:
                outs = self._list_images(out_dir)
                if outs:
                    out_path = outs[0]

            if out_path is None:
                raise RuntimeError("infer.py completed but no output image found in out_dir.")

            out_bgr = cv2.imread(out_path, cv2.IMREAD_COLOR)
            if out_bgr is None:
                raise RuntimeError(f"cv2.imread failed for output image: {out_path}")

            meta["applied"] = True
            meta["output_shape"] = [int(out_bgr.shape[0]), int(out_bgr.shape[1])]
            meta["output_path_used"] = out_path
            return RectifyResult(image=out_bgr, meta=meta)

        except Exception as e:
            meta["error"] = f"{type(e).__name__}: {e}"
            if self.config.strict:
                raise
            meta["warning"] = "DewarpNet failed; passthrough."
            return RectifyResult(image=image_bgr, meta=meta)

        finally:
            if self.config.keep_debug_files:
                meta["debug_dir"] = workdir
            else:
                shutil.rmtree(workdir, ignore_errors=True)
