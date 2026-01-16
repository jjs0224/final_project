# 0) 통합 실행코드
python menu_assistant/worker/worker_app/pipeline/orchestrator.py --image Upload_Images/image13.jpg --use-rerank --top-k 20 --rerank-top-k 5


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
python -m menu_assistant.worker.worker_app.pipeline.steps.step_04_rag_match ^
  --run_id 20260113_121958 ^
  --top_k 20 ^
  --rerank_top_k 5 ^
  --use_rerank
# ChromaDB build
python -m menu_assistant.worker.scripts.build_chroma_index

#reduce_dataset
"""
python menu_assistant/data/datasets/raw/reduce_Dataset.py ^
  --input "C:\Users\201\Desktop\PGHfolder\Final_project\AI\menu_assistant\data\datasets\raw\menu_final_with_allergen.json" ^
  --output "C:\Users\201\Desktop\PGHfolder\Final_project\AI\menu_assistant\data\datasets\raw\menu_representatives_250.json" ^
  --mapping_out "C:\Users\201\Desktop\PGHfolder\Final_project\AI\menu_assistant\data\datasets\raw\menu_representatives_250_mapping.json" ^
  --target_n 250
"""