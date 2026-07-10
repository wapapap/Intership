"""Direct GPU training test."""
from ultralytics import YOLO

model = YOLO('yolo11n')
model.train(
    data='datasets/PCB/data.yaml',
    epochs=10,
    imgsz=640,
    batch=16,
    device=0,          # GPU
    optimizer='SGD',
    lr0=0.01,
    project='runs/train',
    name='gpu_test',
    exist_ok=True,
    verbose=True,
)
print("\nDone! Check runs/train/gpu_test/")
