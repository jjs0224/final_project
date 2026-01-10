"""Pipeline orchestrator: runs end-to-end processing for one input image.

Design:
- Each step lives in worker_app/pipeline/steps and exposes a `run(ctx)` function.
- ctx should carry run_id, paths, user profile, etc.
"""

def run_pipeline(ctx):
    # Import locally to keep dependencies modular
    from .steps import (
        step_01_rectify,
        step_02_ocr,
        step_03_normalize,
        step_04_rag_match,
        step_05_risk_score,
        step_06_translate,
        step_07_overlay,
    )

    ctx = step_01_rectify.run(ctx)
    ctx = step_02_ocr.run(ctx)
    ctx = step_03_normalize.run(ctx)
    ctx = step_04_rag_match.run(ctx)
    ctx = step_05_risk_score.run(ctx)
    ctx = step_06_translate.run(ctx)
    ctx = step_07_overlay.run(ctx)
    return ctx
