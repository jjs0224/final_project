# AI/preprocess_korean_menu.py
# 좌표 불변(geometry invariance) 전처리: resize/rotate/warp 없음
# - 메뉴판/한글 OCR 정확도 개선용
# - 기하학적 변형을 하지 않으므로 OCR box 좌표가 원본과 동일하게 유지됩니다.

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Tuple

import cv2
import numpy as np

Mode = Literal[
    "gray",
    "clahe",
    "clahe_sharp",
    "clahe_denoise_sharp",
    "adaptive_bin",
    "otsu_bin",
]


@dataclass
class PreprocessConfig:
    # 기본 모드: 한글 메뉴판에 가장 무난
    mode: Mode = "clahe_denoise_sharp"

    # CLAHE
    clahe_clip_limit: float = 2.0
    clahe_tile_grid_size: Tuple[int, int] = (8, 8)

    # Denoise (너무 세면 글자 획이 얇아질 수 있어 기본값 보수적으로)
    use_bilateral: bool = True
    bilateral_d: int = 7
    bilateral_sigma_color: float = 40.0
    bilateral_sigma_space: float = 40.0

    # Sharpen (언샵 마스크)
    sharpen_amount: float = 1.0   # 0.6~1.6 사이 추천
    sharpen_sigma: float = 1.0    # 0.8~1.6 사이 추천

    # Adaptive threshold (조명 불균형 심할 때만)
    adaptive_block_size: int = 31  # 홀수
    adaptive_C: int = 7

    # 최종 출력 타입
    # - PaddleOCR에 바로 넣으려면 bgr 권장
    output: Literal["gray", "bgr"] = "bgr"


def _to_gray(img_bgr: np.ndarray) -> np.ndarray:
    if img_bgr is None:
        raise ValueError("Input image is None.")
    if img_bgr.ndim == 2:
        return img_bgr
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)


def _apply_clahe(gray: np.ndarray, cfg: PreprocessConfig) -> np.ndarray:
    clahe = cv2.createCLAHE(
        clipLimit=float(cfg.clahe_clip_limit),
        tileGridSize=tuple(cfg.clahe_tile_grid_size),
    )
    return clahe.apply(gray)


def _bilateral(gray: np.ndarray, cfg: PreprocessConfig) -> np.ndarray:
    # bilateral은 가장자리(글자 획)를 비교적 보존하면서 노이즈를 줄임
    return cv2.bilateralFilter(
        gray,
        d=int(cfg.bilateral_d),
        sigmaColor=float(cfg.bilateral_sigma_color),
        sigmaSpace=float(cfg.bilateral_sigma_space),
    )


def _unsharp(gray: np.ndarray, cfg: PreprocessConfig) -> np.ndarray:
    # Unsharp mask: gray + amount*(gray - blur)
    sigma = float(cfg.sharpen_sigma)
    amount = float(cfg.sharpen_amount)

    blur = cv2.GaussianBlur(gray, (0, 0), sigmaX=sigma, sigmaY=sigma)
    sharpened = cv2.addWeighted(gray, 1.0 + amount, blur, -amount, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def preprocess_menu_image(img_bgr: np.ndarray, cfg: Optional[PreprocessConfig] = None) -> np.ndarray:
    """좌표 불변 전처리.

    - 입력과 동일한 W,H 유지(좌표 불변).
    - 기하학적 변환(rotate/resize/warp)을 하지 않는다.
    - 픽셀 값만 개선(CLAHE/denoise/sharpen/bin).

    Returns:
        np.ndarray: cfg.output에 따라 gray 또는 bgr
    """
    if cfg is None:
        cfg = PreprocessConfig()

    gray = _to_gray(img_bgr)

    if cfg.mode == "gray":
        out = gray

    elif cfg.mode == "clahe":
        out = _apply_clahe(gray, cfg)

    elif cfg.mode == "clahe_sharp":
        out = _unsharp(_apply_clahe(gray, cfg), cfg)

    elif cfg.mode == "clahe_denoise_sharp":
        x = _apply_clahe(gray, cfg)
        if cfg.use_bilateral:
            x = _bilateral(x, cfg)
        out = _unsharp(x, cfg)

    elif cfg.mode == "adaptive_bin":
        x = _apply_clahe(gray, cfg)
        # 조명 편차가 심한 메뉴판에 효과적(단, 글자 획이 약해질 수 있음)
        bs = int(cfg.adaptive_block_size)
        if bs % 2 == 0:
            bs += 1
        out = cv2.adaptiveThreshold(
            x,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            bs,
            int(cfg.adaptive_C),
        )

    elif cfg.mode == "otsu_bin":
        x = _apply_clahe(gray, cfg)
        _, out = cv2.threshold(x, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    else:
        raise ValueError(f"Unknown mode: {cfg.mode}")

    if cfg.output == "gray":
        return out

    # PaddleOCR에 넣기 쉬운 BGR로 변환(좌표 영향 없음)
    return cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)
