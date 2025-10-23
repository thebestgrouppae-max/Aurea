from ultralytics import YOLO

model = YOLO("yolo11x.pt")

results = model.train(
    data="lvis_subset_50.yaml",
    epochs=50,
    imgsz=640,
    batch=16,          # VRAM
    workers=4,        # RAM/CPU
    cache=False,      # LVIS es muy grande, no usar cache
    device=0
)
