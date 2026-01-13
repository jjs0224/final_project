# 0) 통합 실행코드
python -m menu_assistant.worker.worker_app.pipeline.orchestrator --image Upload_Images\image9.jpg

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

python -m menu_assistant.worker.worker_app.pipeline.steps.step_02_ocr ^
  --image Upload_Images/image7.jpg ^
  --out   menu_assistant/data/runs/20260112_181356/ocr/ocr.json ^
  --vis   menu_assistant/data/runs/20260112_181356/ocr/ocr_vis.jpg

# 3) normalize 실행
python -m menu_assistant.worker.worker_app.pipeline.steps.step_03_normalize --runs-root "C:\Users\201\Desktop\PGHfolder\Final_project\AI\menu_assistant\data\runs" --run-id 20260112_181356

# 4) rag match 메뉴명만 선매칭
python -m menu_assistant.worker.worker_app.pipeline.steps.step_04_rag_match --run_id 20260113_121958 --save_candidates_k 5 --include_debug

# ChromaDB build
python -m menu_assistant.worker.scripts.build_chroma_index