# 1) 보정만 수행 (photometric-only)
python -m worker_app.pipeline.steps.01_rectify --input Upload_Images/menu.jpg --backend none

# 2) 보정 + (기하 모델 백엔드) 사용 (아직 placeholder이므로 현재는 passthrough)
python -m worker_app.pipeline.steps.01_rectify --input Upload_Images/menu.jpg --backend doctr
