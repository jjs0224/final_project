# 1) 보정만 수행 (photometric-only)
python -m menu_assistant.worker.worker_app.pipeline.steps.step_01_rectify --input Upload_Images/image1.jpg --backend none
backend = [doctr,dewarpnet,docunet]
python -m menu_assistant.worker.worker_app.pipeline.steps.step_01_rectify --input Upload_Images/image1.jpg --backend doctr
python -m menu_assistant.worker.worker_app.pipeline.steps.step_01_rectify --input Upload_Images/image1.jpg --backend docunet
python -m menu_assistant.worker.worker_app.pipeline.steps.step_01_rectify --input Upload_Images/image8.jpg --backend auto
# 2) paddleocr 작동
python -m menu_assistant.worker.worker_app.pipeline.steps.step_02_ocr --run_id 20260112_181356 --dump_raw
  --image menu_assistant/data/runs/20260112_181356/rectify/rectified.jpg ^
  --out   menu_assistant/data/runs/20260112_181356/ocr/ocr.json ^
  --vis   menu_assistant/data/runs/20260112_181356/ocr/ocr_vis.jpg


