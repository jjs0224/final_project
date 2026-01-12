from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, Union

import cv2
import numpy as np

from .base import RectifyBackend, RectifyResult


class DoctrBackend(RectifyBackend):
    """
    DocTR backend: orientation(회전) 감지 + OpenCV 회전 적용

    - rectify.py의 _get_backend()가 호출하는 생성자 시그니처와 호환:
        DoctrBackend(device=device, model_dir=model_dir)

    - rectify()는 RectifyResult(image, meta)를 반환해야 함.

    동작:
      1) doctr가 없으면 RuntimeError
      2) doctr orientation predictor를 로드(가능할 때만)
      3) 입력 이미지(BGR)를 RGB로 바꿔 predictor에 넣고 각도 추정
      4) 90/180/270이면 cv2.rotate로 실제 회전 적용
    """

    name = "doctr"

    def __init__(self, device: str = "cpu", model_dir: Optional[str] = None):
        super().__init__(device=device, model_dir=model_dir)

        self._doctr = None
        #원인 중심에러 메세지 제공
        self._import_error: Optional[BaseException] = None

        # lazy model cache
        self._orientation_predictor = None
        self._models_ready = False

        try:
            import doctr as _doctr  # type: ignore
        except Exception as e:
            self._import_error = e
            self._doctr = None
        else:
            self._import_error = None
            self._doctr = _doctr

    # -------------------------
    # internal helpers
    # -------------------------
    #doctr 사용불가능하면 추후과정다에러가나기때문에 사전에 에러로 끊어줘야한다.
    def _ensure_available(self) -> None:
        if self._import_error is not None or self._doctr is None:
            raise RuntimeError(
                "DocTR backend requested, but doctr is not installed/available.\n"
                "Fix options:\n"
                "  1) pip install python-doctr (and a backend: torch or tensorflow)\n"
                "  2) Or run with --backend none\n"
                f"Original error: {self._import_error!r}"
            )
    #최소한의 검증작업 shape기준으로
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
    #opencv는 bgr 반이기때문에 rgb로 변경
    @staticmethod
    def _bgr_to_rgb(image_bgr: np.ndarray) -> np.ndarray:
        return image_bgr[:, :, ::-1].copy()

    def _lazy_init_models(self) -> Dict[str, Any]:
        self._ensure_available()

        if self._models_ready:
            return {"models_ready": True, "init": "cached"}

        # orientation predictor 준비 (버전 차이를 고려해 try)
        predictor = None
        err = None
        try:
            from doctr.models import orientation_predictor  # type: ignore

            # 보통 pretrained=True 형태
            predictor = orientation_predictor(pretrained=True)
        except Exception as e:
            err = e
            predictor = None

        self._orientation_predictor = predictor
        self._models_ready = True

        meta = {"models_ready": True, "init": "orientation_predictor" if predictor is not None else "none"}
        if err is not None:
            meta["orientation_predictor_error"] = repr(err)
        return meta

    @staticmethod
    def _angle_from_doctr_output(out: Any) -> Optional[int]:
        """
        doctr predictor 출력 형태가 버전/백엔드에 따라 달라질 수 있어서
        여러 케이스를 최대한 흡수해 '각도(int)'로 정규화한다.

        기대 가능한 각도: 0 / 90 / 180 / 270
        """
        # (A) out이 dict 형태로 angle을 직접 포함
        if isinstance(out, dict):
            for k in ("angle", "orientation", "rotation"):
                if k in out:
                    val = out[k]
                    return DoctrBackend._normalize_angle(val)

        # (B) out이 list/tuple이고 첫 요소에 정보가 들어있는 경우
        if isinstance(out, (list, tuple)) and len(out) > 0:
            # 흔한 케이스: batch 출력 -> 첫 번째만 사용
            first = out[0]
            # 재귀적으로 한 번 더 파싱
            ang = DoctrBackend._angle_from_doctr_output(first)
            if ang is not None:
                return ang

            # list 자체가 확률/점수 벡터인 경우
            # e.g. [p0,p90,p180,p270]
            if all(isinstance(x, (int, float, np.floating, np.integer)) for x in out) and len(out) in (4,):
                arr = np.array(out, dtype=float)
                idx = int(arr.argmax())
                return [0, 90, 180, 270][idx]

        # (C) numpy array: (4,) 또는 (1,4) 확률 벡터일 수 있음
        if isinstance(out, np.ndarray):
            arr = out
            if arr.ndim == 2 and arr.shape[0] == 1:
                arr = arr[0]
            if arr.ndim == 1 and arr.shape[0] == 4:
                idx = int(np.argmax(arr))
                return [0, 90, 180, 270][idx]

        # (D) 스칼라/문자열로 들어오는 경우
        return DoctrBackend._normalize_angle(out)

    @staticmethod
    def _normalize_angle(val: Any) -> Optional[int]:
        """
        다양한 타입(int/float/str)을 0/90/180/270 중 하나로 정규화.
        """
        if val is None:
            return None

        # 숫자라면
        if isinstance(val, (int, np.integer)):
            v = int(val)
            return v % 360 if v % 90 == 0 else None

        if isinstance(val, (float, np.floating)):
            v = int(round(float(val)))
            return v % 360 if v % 90 == 0 else None

        # 문자열이라면
        if isinstance(val, str):
            s = val.strip().lower()
            mapping = {
                "0": 0,
                "90": 90,
                "180": 180,
                "270": 270,
                "rot0": 0,
                "rot90": 90,
                "rot180": 180,
                "rot270": 270,
                "upright": 0,
            }
            if s in mapping:
                return mapping[s]
            # "90deg" 같은 형태
            for key in ("0", "90", "180", "270"):
                if key in s:
                    return int(key)
        return None

    @staticmethod
    def _apply_rotation_bgr(image_bgr: np.ndarray, angle: int) -> np.ndarray:
        """
        90도 단위 회전만 적용 (overlay 좌표계가 확 바뀌는 것을 최소화/명확화)
        """
        a = angle % 360
        if a == 0:
            return image_bgr
        if a == 90:
            return cv2.rotate(image_bgr, cv2.ROTATE_90_CLOCKWISE)
        if a == 180:
            return cv2.rotate(image_bgr, cv2.ROTATE_180)
        if a == 270:
            return cv2.rotate(image_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
        # 여기로 오면 90 단위가 아닌 값인데, 우리는 적용하지 않음
        return image_bgr

    # -------------------------
    # public
    # -------------------------
    def rectify(self, image_bgr: np.ndarray) -> RectifyResult:
        #최소검증
        h, w = self._validate_image(image_bgr)
        self._ensure_available()
        init_meta = self._lazy_init_models()

        meta: Dict[str, Any] = {
            "backend": self.name,
            "device": self.device,
            "model_dir": self.model_dir,
            "input_shape": [h, w],
            "init": init_meta,
            "orientation": {
                "enabled": True,
                "predictor_available": self._orientation_predictor is not None,
            },
            "applied": False,
        }

        # predictor가 없으면 passthrough
        if self._orientation_predictor is None:
            meta["warning"] = "DocTR orientation predictor unavailable; passthrough."
            meta["output_shape"] = [h, w]
            return RectifyResult(image=image_bgr, meta=meta)

        # predictor 실행
        try:
            rgb = self._bgr_to_rgb(image_bgr)

            # doctr predictor는 보통 batch 입력을 받는 형태가 많아 [rgb]로 감쌈
            pred_out = self._orientation_predictor([rgb])

            angle = self._angle_from_doctr_output(pred_out)
            meta["orientation"]["raw_output_type"] = type(pred_out).__name__
            meta["orientation"]["angle"] = angle

            if angle in (0, 90, 180, 270):
                rotated = self._apply_rotation_bgr(image_bgr, angle)
                meta["applied"] = (angle != 0)
                meta["orientation"]["applied"] = meta["applied"]
                meta["output_shape"] = [int(rotated.shape[0]), int(rotated.shape[1])]
                return RectifyResult(image=rotated, meta=meta)

            # angle 파싱 실패 또는 비정상 값이면 적용하지 않음
            meta["orientation"]["applied"] = False
            meta["warning"] = "Orientation predicted but could not normalize to 0/90/180/270; passthrough."
            meta["output_shape"] = [h, w]
            return RectifyResult(image=image_bgr, meta=meta)

        except Exception as e:
            meta["orientation"]["error"] = repr(e)
            meta["warning"] = "Orientation inference failed; passthrough."
            meta["output_shape"] = [h, w]
            return RectifyResult(image=image_bgr, meta=meta)
