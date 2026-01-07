from pathlib import Path
from AI.PaddleOCR_core import run_ocr_and_save_json

def main():
    BASE_DIR = Path(__file__).resolve().parent
    img_dir = (BASE_DIR / "Upload_Images").resolve()
    out_root = (BASE_DIR / "ocr_output").resolve()

    exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    image_paths = sorted([p for p in img_dir.iterdir() if p.is_file() and p.suffix.lower() in exts])

    ok, fail = 0, 0
    for image_path in image_paths:
        print("\n" + "=" * 60)
        print(f"[RUN] {image_path.name}")
        try:
            run_ocr_and_save_json(
                image_path=image_path,
                out_root=out_root,   # ✅ core가 stem 폴더 생성/정리
                det_limit_side_len=4000,
                det_limit_type="max",
                use_pre_rectify=True,
            )
            ok += 1
        except Exception as e:
            fail += 1
            print(f"[FAIL] {image_path.name}: {e}")

    print("\n" + "=" * 60)
    print(f"Done. success={ok}, failed={fail}, total={len(image_paths)}")

if __name__ == "__main__":
    main()
