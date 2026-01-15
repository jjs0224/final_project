from __future__ import annotations

import sys
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List


# ============================================================
# Utilities
# ============================================================
def make_run_id() -> str:
    # runs/20260113_114232 형태
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def run_cmd(cmd: List[str]) -> None:
    """
    Run a command and raise on failure.
    """
    print("\n[RUN]", " ".join(cmd))
    p = subprocess.run(cmd, shell=False)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed (exit={p.returncode}): {' '.join(cmd)}")


def ensure_exists(path: Path, msg: str) -> None:
    if not path.exists():
        raise RuntimeError(f"{msg}: {path}")


# ============================================================
# Orchestrator
# ============================================================
@dataclass
class Step1Options:
    backend: str = "auto"     # {none,doctr,dewarpnet,docunet,auto}
    device: str = "cpu"
    model_dir: Optional[str] = None
    gamma: float = 1.0
    clahe_clip: float = 2.0
    shadow_strength: float = 0.0


@dataclass
class Step2Options:
    # PaddleOCR / OCR options (pass-through)
    lang: str = "korean"
    det_limit_side_len: int = 4000
    det_limit_type: str = "max"
    use_doc_unwarping: bool = False
    use_textline_orientation: bool = False
    det_model_dir: Optional[str] = None
    rec_model_dir: Optional[str] = None
    cls_model_dir: Optional[str] = None

    use_preprocess: bool = False
    preprocess_mode: Optional[str] = None

    dump_raw: bool = False
    out: Optional[str] = None
    vis: Optional[str] = None


@dataclass
class Step3Options:
    min_len: int = 2
    line_y_tol: int = 20
    merge_gap_px: int = 25
    min_score: float = 0.0


@dataclass
class Step4Options:
    # RAG match options
    top_k: int = 20
    rerank_top_k: int = 5
    score_threshold: float = 0.85
    ambiguous_gap: float = 0.03
    use_rerank: bool = True
    include_debug: bool = False


class PipelineOrchestrator:
    """
    image -> step_01_rectify -> step_02_ocr -> step_03_normalize -> step_04_rag_match -> (optional) check step_03 output
    """

    def __init__(self, runs_root: Path):
        self.runs_root = runs_root
        # ✅ FIX: runs_root = .../data/runs  -> data_dir = .../data
        # (기존 코드는 self.data_dir=runs_root로 설정되어 Step04 경로가 꼬일 수 있음)
        self.data_dir = runs_root.parent

    def run(
        self,
        image_path: Path,
        run_id: Optional[str] = None,
        *,
        step1: Optional[Step1Options] = None,
        step2: Optional[Step2Options] = None,
        step3: Optional[Step3Options] = None,
        step4: Optional[Step4Options] = None,
        do_check: bool = True,
        check_keywords: Optional[List[str]] = None,
        show_structured: bool = True,
        run_step4: bool = True,
    ) -> Path:
        if not image_path.exists():
            raise FileNotFoundError(f"Input image not found: {image_path}")

        step1 = step1 or Step1Options()
        step2 = step2 or Step2Options()
        step3 = step3 or Step3Options()
        step4 = step4 or Step4Options()

        run_id = run_id or make_run_id()
        run_dir = self.runs_root / run_id

        rectify_img = run_dir / "rectify" / "rectified.jpg"
        ocr_json = run_dir / "ocr" / "ocr.json"
        normalize_json = run_dir / "normalize" / "normalize.json"
        rag_match_json = run_dir / "rag_match" / "rag_match.json"

        # ----------------------------------------------------
        # Step 01: Rectify (정식 인자: --run_id, --data_dir)
        # ----------------------------------------------------
        cmd1 = [
            sys.executable, "-m",
            "menu_assistant.worker.worker_app.pipeline.steps.step_01_rectify",
            "--input", str(image_path),
            "--run_id", run_id,
            "--data_dir", str(self.data_dir),
            "--backend", step1.backend,
            "--device", step1.device,
            "--gamma", str(step1.gamma),
            "--clahe_clip", str(step1.clahe_clip),
            "--shadow_strength", str(step1.shadow_strength),
        ]
        if step1.model_dir:
            cmd1 += ["--model_dir", step1.model_dir]

        run_cmd(cmd1)
        ensure_exists(rectify_img, "Step01 expected output missing (rectified image)")

        # ----------------------------------------------------
        # Step 02: OCR
        # ----------------------------------------------------
        cmd2 = [
            sys.executable, "-m",
            "menu_assistant.worker.worker_app.pipeline.steps.step_02_ocr",
            "--run_id", run_id,
            "--data_dir", str(self.data_dir),
            "--lang", step2.lang,
            "--det_limit_side_len", str(step2.det_limit_side_len),
            "--det_limit_type", step2.det_limit_type,
        ]

        if step2.use_doc_unwarping:
            cmd2 += ["--use_doc_unwarping"]
        if step2.use_textline_orientation:
            cmd2 += ["--use_textline_orientation"]
        if step2.det_model_dir:
            cmd2 += ["--det_model_dir", step2.det_model_dir]
        if step2.rec_model_dir:
            cmd2 += ["--rec_model_dir", step2.rec_model_dir]
        if step2.cls_model_dir:
            cmd2 += ["--cls_model_dir", step2.cls_model_dir]

        if step2.use_preprocess:
            cmd2 += ["--use_preprocess"]
            if step2.preprocess_mode:
                cmd2 += ["--preprocess_mode", step2.preprocess_mode]

        if step2.dump_raw:
            cmd2 += ["--dump_raw"]

        # out/vis를 지정하면 기본 경로를 오버라이드
        if step2.out:
            cmd2 += ["--out", step2.out]
        if step2.vis:
            cmd2 += ["--vis", step2.vis]

        run_cmd(cmd2)

        ocr_json_check = Path(step2.out) if step2.out else ocr_json
        ensure_exists(ocr_json_check, "Step02 expected output missing (ocr json)")

        # ----------------------------------------------------
        # Step 03: Normalize
        # ----------------------------------------------------
        cmd3 = [
            sys.executable, "-m",
            "menu_assistant.worker.worker_app.pipeline.steps.step_03_normalize",
            "--runs-root", str(self.runs_root),
            "--run-id", run_id,
            "--min-len", str(step3.min_len),
            "--line-y-tol", str(step3.line_y_tol),
            "--merge-gap-px", str(step3.merge_gap_px),
            "--min-score", str(step3.min_score),
        ]
        run_cmd(cmd3)
        ensure_exists(normalize_json, "Step03 expected output missing (normalize json)")

        # ----------------------------------------------------
        # Optional: Step 03 Result Check
        # ----------------------------------------------------
        if do_check:
            check_cmd = [
                sys.executable, "-m",
                "menu_assistant.worker.worker_app.utils.check_step_03_result",
                "--json", str(normalize_json),
            ]
            if show_structured:
                check_cmd += ["--show-structured"]
            if check_keywords:
                check_cmd += ["--keywords"] + list(check_keywords)

            run_cmd(check_cmd)

        # ----------------------------------------------------
        # Step 04: RAG Match (+ optional rerank)
        # ----------------------------------------------------
        if run_step4:
            cmd4 = [
                sys.executable, "-m",
                "menu_assistant.worker.worker_app.pipeline.steps.step_04_rag_match",
                "--run_id", run_id,
                "--data_dir", str(self.data_dir),
                "--top_k", str(step4.top_k),
                "--rerank_top_k", str(step4.rerank_top_k),
                "--score_threshold", str(step4.score_threshold),
                "--ambiguous_gap", str(step4.ambiguous_gap),
            ]
            if step4.use_rerank:
                cmd4 += ["--use_rerank"]
            else:
                cmd4 += ["--no_rerank"]

            if step4.include_debug:
                cmd4 += ["--include_debug"]

            run_cmd(cmd4)
            ensure_exists(rag_match_json, "Step04 expected output missing (rag_match json)")

        print("\n=== PIPELINE DONE (01~04) ===")
        print(f"run_dir        : {run_dir}")
        print(f"rectified.jpg  : {rectify_img}")
        print(f"ocr.json       : {ocr_json_check}")
        print(f"normalize.json : {normalize_json}")
        if run_step4:
            print(f"rag_match.json : {rag_match_json}")

        return run_dir


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Pipeline Orchestrator: step_01 -> step_02 -> step_03 -> step_04")

    p.add_argument("--image", required=True, help="Input image path")
    p.add_argument("--runs-root", default="menu_assistant/data/runs", help="Runs root directory")
    p.add_argument("--run-id", default=None, help="Optional run id. If omitted, auto-generated.")

    # ---------------- Step1 passthrough ----------------
    p.add_argument("--backend", default="auto", choices=["none", "doctr", "dewarpnet", "docunet", "auto"])
    p.add_argument("--device", default="cpu")
    p.add_argument("--model-dir", default="menu_assistant/worker/worker_app/vision/metrics/DewarpNet_master")
    p.add_argument("--gamma", type=float, default=1.0)
    p.add_argument("--clahe-clip", type=float, default=2.0)
    p.add_argument("--shadow-strength", type=float, default=0.0)

    # ---------------- Step2 passthrough ----------------
    p.add_argument("--lang", default="korean")
    p.add_argument("--det-limit-side-len", type=int, default=4000)
    p.add_argument("--det-limit-type", default="max")
    p.add_argument("--use-doc-unwarping", action="store_true")
    p.add_argument("--use-textline-orientation", action="store_true")
    p.add_argument("--det-model-dir", default=None)
    p.add_argument("--rec-model-dir", default=None)
    p.add_argument("--cls-model-dir", default=None)

    p.add_argument("--use-preprocess", action="store_true")
    p.add_argument("--preprocess-mode", default=None)

    p.add_argument("--dump-raw", action="store_true")
    p.add_argument("--ocr-out", default=None, help="Override step2 --out path (default: <run>/ocr/ocr.json)")
    p.add_argument("--ocr-vis", default=None, help="Override step2 --vis path (default: <run>/ocr/ocr_vis.jpg)")

    # ---------------- Step3 passthrough ----------------
    p.add_argument("--min-len", type=int, default=2)
    p.add_argument("--line-y-tol", type=int, default=20)
    p.add_argument("--merge-gap-px", type=int, default=25)
    p.add_argument("--min-score", type=float, default=0.0)

    # ---------------- Step4 passthrough ----------------
    p.add_argument("--run-step4", action="store_true", help="Run step4 (default: on)")
    p.add_argument("--no-step4", action="store_true", help="Skip step4")
    p.add_argument("--top-k", type=int, default=20)
    p.add_argument("--rerank-top-k", type=int, default=5)
    p.add_argument("--score-threshold", type=float, default=0.85)
    p.add_argument("--ambiguous-gap", type=float, default=0.03)
    p.add_argument("--use-rerank", action="store_true")
    p.add_argument("--no-rerank", action="store_true")
    p.add_argument("--rag-debug", action="store_true")

    # ---------------- Check options ----------------
    p.add_argument("--no-check", action="store_true", help="Skip step_03 result check")
    p.add_argument("--check-keywords", nargs="*", default=None)
    p.add_argument("--no-structured", action="store_true", help="Do not print structured fields in checker")

    args = p.parse_args()

    orch = PipelineOrchestrator(Path(args.runs_root))

    step1 = Step1Options(
        backend=args.backend,
        device=args.device,
        model_dir=args.model_dir,
        gamma=args.gamma,
        clahe_clip=args.clahe_clip,
        shadow_strength=args.shadow_strength,
    )

    step2 = Step2Options(
        lang=args.lang,
        det_limit_side_len=args.det_limit_side_len,
        det_limit_type=args.det_limit_type,
        use_doc_unwarping=args.use_doc_unwarping,
        use_textline_orientation=args.use_textline_orientation,
        det_model_dir=args.det_model_dir,
        rec_model_dir=args.rec_model_dir,
        cls_model_dir=args.cls_model_dir,
        use_preprocess=args.use_preprocess,
        preprocess_mode=args.preprocess_mode,
        dump_raw=args.dump_raw,
        out=args.ocr_out,
        vis=args.ocr_vis,
    )

    step3 = Step3Options(
        min_len=args.min_len,
        line_y_tol=args.line_y_tol,
        merge_gap_px=args.merge_gap_px,
        min_score=args.min_score,
    )

    # Step4 옵션 구성
    use_rerank = True
    if args.no_rerank:
        use_rerank = False
    if args.use_rerank:
        use_rerank = True

    step4 = Step4Options(
        top_k=args.top_k,
        rerank_top_k=args.rerank_top_k,
        score_threshold=args.score_threshold,
        ambiguous_gap=args.ambiguous_gap,
        use_rerank=use_rerank,
        include_debug=args.rag_debug,
    )

    run_step4 = True
    if args.no_step4:
        run_step4 = False
    if args.run_step4:
        run_step4 = True

    orch.run(
        image_path=Path(args.image),
        run_id=args.run_id,
        step1=step1,
        step2=step2,
        step3=step3,
        step4=step4,
        do_check=(not args.no_check),
        check_keywords=args.check_keywords,
        show_structured=(not args.no_structured),
        run_step4=run_step4,
    )

