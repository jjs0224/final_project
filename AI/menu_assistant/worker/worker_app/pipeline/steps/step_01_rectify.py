from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from menu_assistant.worker.worker_app.vision.rectify import (
    RectifyConfig,
    rectify_image,
    read_image_bgr,
    write_image_bgr,
)

# 실행한 시간을 id값으로 반환
def _default_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def main():
    # -h 이 코드의 도움말 부분
    parser = argparse.ArgumentParser(description="Step 01 - Rectify menu image (no text detection)")
    # 원본 이미지의 경로를 정의하는 부분 required는 필수인지 선택인지 정하는 부분
    parser.add_argument("--input", required=True, help="Path to original image")
    # run_id 는 파일명을 지정해주고싶을때 ,data_dir 은 결과값 저장위치,(menu_assistant/data/runs/{run_id}/rectify/rectified.jpg)
    parser.add_argument("--run_id", default=None, help="Run ID (default: timestamp)")
    parser.add_argument("--data_dir", default="menu_assistant/data/runs", help="Base output dir")
    #default none 값은 photometric-only(조명/노이즈/대비 등)만 조정 choices에 있는 모델을 선택 가능
    parser.add_argument("--backend", default="auto", choices=["none", "doctr", "dewarpnet", "docunet","auto"])
    #가중치 값을 사용하거나 cuda 이용할시에 주는 옵션
    parser.add_argument("--device", default="cpu", help="cpu|cuda (depends on backend impl)")
    parser.add_argument("--model_dir", default=None, help="Optional model directory for backend weights")

    # Simple photometric knobs (optional) 실행코드에서 쉽게 조정할수있도록 구성
    #--gamma: 감마 보정 값 (밝기/중간톤 조정)--clahe_clip: CLAHE(국소 대비 향상) 강도--shadow_strength: 그림자/조명 보정 강도
    parser.add_argument("--gamma", type=float, default=1.15)
    parser.add_argument("--clahe_clip", type=float, default=2.0)
    parser.add_argument("--shadow_strength", type=float, default=0.85)
    #사용자가 입력한 --input, --gamma 등이 args 객체에 들어갑니다.예: args.input, args.gamma처럼 접근합니다.
    args = parser.parse_args()
    #run_id 값을 cli때 지정한값을 쓰거나 위에 구성해놓은 타임스탭형식으로쓸수있게 표현
    run_id = args.run_id or _default_run_id()
    #주소값에 대한설정 위에서 설정한 base = {data_dir}/{run_id}
    base = Path(args.data_dir) / "runs" / run_id
    input_dir = base / "input"
    rectify_dir = base / "rectify"
    #parents는 중간 폴더가 없어도 생성할것인지 ,exist_ok는 이미 있어도 오류를 발생할지안할지
    input_dir.mkdir(parents=True, exist_ok=True)
    rectify_dir.mkdir(parents=True, exist_ok=True)

    # Copy original path reference only (you can physically copy the file if you want)
    # Here we just record it in meta; if you prefer: shutil.copy(args.input, input_dir/"original.jpg")
    original_path = Path(args.input)

    img = read_image_bgr(str(original_path))
    #보정 파이프라인의 전체설정
    cfg = RectifyConfig(
        backend=args.backend,
        device=args.device,
        model_dir=args.model_dir,
    )
    #기본갑 + cli에서 받은값으로 덮어씌우기
    cfg.enhance.gamma = float(args.gamma)
    cfg.enhance.clahe_clip_limit = float(args.clahe_clip)
    cfg.illumination.strength = float(args.shadow_strength)
    #실제 보정을 실행하는 부분
    res = rectify_image(img, cfg)
    #보정이후값 저장위치 설정과 이름 고정
    out_img_path = rectify_dir / "rectified.jpg"
    out_meta_path = rectify_dir / "rectify_meta.json"
    #보정된 이미지 저장하기
    write_image_bgr(str(out_img_path), res.image)

    meta = {
        "run_id": run_id,
        "input_image": str(original_path),
        "rectified_image": str(out_img_path),
        **res.meta,
    }
    #보정된 이비지의 meta값 저장하기
    out_meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] rectified image: {out_img_path}")
    print(f"[OK] rectify meta   : {out_meta_path}")


if __name__ == "__main__":
    main()
