# 1) 보정만 수행 (photometric-only)
python -m menu_assistant.worker.worker_app.pipeline.steps.step_01_rectify --input Upload_Images/image1.jpg --backend none
backend = [doctr,dewarpnet,docunet]
python -m menu_assistant.worker.worker_app.pipeline.steps.step_01_rectify --input Upload_Images/image1.jpg --backend doctr
python -m menu_assistant.worker.worker_app.pipeline.steps.step_01_rectify --input Upload_Images/image1.jpg --backend docunet
python -m menu_assistant.worker.worker_app.pipeline.steps.step_01_rectify --input Upload_Images/image8.jpg --backend auto
# 2) 보정 + (기하 모델 백엔드) 사용 (아직 placeholder이므로 현재는 passthrough)
python -m worker_app.pipeline.steps.01_rectify --input Upload_Images/menu.jpg --backend doctr
