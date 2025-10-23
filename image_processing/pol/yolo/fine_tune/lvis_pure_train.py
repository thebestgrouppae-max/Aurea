from ultralytics import YOLO

model = YOLO("yolo11n.pt")

results = model.train(
    data="lvis_subset_pure.yaml",
    epochs=50,
    imgsz=640,
    batch=8,          # VRAM
    workers=2,        # RAM/CPU
    cache=False,      # LVIS es muy grande, mejor no usar cache
    device=0
)
