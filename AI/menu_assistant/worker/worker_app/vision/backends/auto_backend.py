from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np

from .base import RectifyBackend, RectifyResult
from .docunet_backend import DocUNetBackend, DocUNetConfig
from .dewarpnet_backend import DewarpNetBackend, DewarpNetConfig
from ..metrics.dewarp_triggers import compute_dewarp_trigger


@dataclass(frozen=True)
class AutoConfig:
    """
    Auto backend policy:
      - run DocUNet first (fast + stable)
      - if trigger score is high AND dewarp backend is ready -> run DewarpNet
      - select best output with conservative acceptance rules
    """
    # trigger threshold: higher => less often dewarp (safer)
    trigger_threshold: float = 0.65

    # require objective improvement to accept dewarp result
    min_score_gain: float = 0.10

    # if DocUNet couldn't find quad, allow DewarpNet as "rescue" when trigger is high
    allow_dewarp_when_docunet_failed: bool = True


class AutoBackend(RectifyBackend):
    name = "auto"

    def __init__(
        self,
        device: str = "cpu",
        model_dir: Optional[str] = None,
        docunet: Optional[DocUNetConfig] = None,
        dewarpnet: Optional[DewarpNetConfig] = None,
        auto: Optional[AutoConfig] = None,
    ):
        super().__init__(device=device, model_dir=model_dir)
        self.docunet_cfg = docunet or DocUNetConfig()
        self.dewarpnet_cfg = dewarpnet or DewarpNetConfig()
        self.auto_cfg = auto or AutoConfig()

        # Sub-backends
        self._docunet = DocUNetBackend(device=device, model_dir=model_dir, config=self.docunet_cfg)
        self._dewarpnet = DewarpNetBackend(device=device, model_dir=model_dir, config=self.dewarpnet_cfg)

    def rectify(self, image_bgr: np.ndarray) -> RectifyResult:
        # 1) DocUNet first
        res_u = self._docunet.rectify(image_bgr)

        # 2) Compute trigger score on DocUNet output image (or input if docunet failed)
        trig = compute_dewarp_trigger(res_u.image)

        meta: Dict[str, Any] = {
            "backend": self.name,
            "device": self.device,
            "model_dir": self.model_dir,
            "auto": {
                "policy": {
                    "trigger_threshold": self.auto_cfg.trigger_threshold,
                    "min_score_gain": self.auto_cfg.min_score_gain,
                    "allow_dewarp_when_docunet_failed": self.auto_cfg.allow_dewarp_when_docunet_failed,
                },
                "trigger": trig,
                "selected": "docunet",
                "decision": {},
            },
            "docunet_meta": res_u.meta,
            "dewarpnet_meta": None,
        }

        # Determine DocUNet success signal (quad found?)
        docunet_quad_found = False
        try:
            docunet_quad_found = bool(res_u.meta.get("opencv", {}).get("find", {}).get("found", False))
        except Exception:
            docunet_quad_found = False

        # 3) Decide whether to attempt DewarpNet
        dewarp_ready = bool(getattr(self._dewarpnet, "ready", False))
        should_try = (trig["score"] >= self.auto_cfg.trigger_threshold) and dewarp_ready

        if (not docunet_quad_found) and self.auto_cfg.allow_dewarp_when_docunet_failed and dewarp_ready:
            # “rescue” path: if docunet failed and trigger says "texty/curvy", allow trying dewarp even if threshold not met
            should_try = should_try or (trig["score"] >= max(0.45, self.auto_cfg.trigger_threshold - 0.15))

        meta["auto"]["decision"]["docunet_quad_found"] = docunet_quad_found
        meta["auto"]["decision"]["dewarp_ready"] = dewarp_ready
        meta["auto"]["decision"]["should_try_dewarpnet"] = should_try

        if not should_try:
            # Keep DocUNet result
            return RectifyResult(image=res_u.image, meta=meta)

        # 4) Try DewarpNet on DocUNet output (preferred) to reduce orientation/perspective noise
        res_d = self._dewarpnet.rectify(res_u.image)
        meta["dewarpnet_meta"] = res_d.meta

        # 5) Compare & select (conservative)
        # We recompute trigger score on dewarped output; if it improves, it likely reduced curvature/line distortion
        trig_d = compute_dewarp_trigger(res_d.image)
        meta["auto"]["trigger_dewarpnet"] = trig_d

        gain = trig_d["score"] - trig["score"]
        meta["auto"]["decision"]["score_gain"] = gain

        # Accept only if objectively better by margin, or if docunet failed and dewarp looks reasonable
        accept = False
        if gain >= self.auto_cfg.min_score_gain:
            accept = True
        elif (not docunet_quad_found) and trig_d["score"] >= trig["score"] and trig_d["score"] >= 0.55:
            accept = True

        meta["auto"]["decision"]["accept_dewarpnet"] = accept

        if accept:
            meta["auto"]["selected"] = "dewarpnet"
            return RectifyResult(image=res_d.image, meta=meta)

        # Otherwise keep DocUNet
        return RectifyResult(image=res_u.image, meta=meta)
