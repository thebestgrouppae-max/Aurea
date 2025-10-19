from ultralytics import YOLO

model = YOLO("yolo11n.pt")

results = model.train(
    data="lvis_supermercado.yaml",
    epochs=50,
    imgsz=640,
    batch=16,          # VRAM
    workers=4,        # RAM/CPU
    cache=False,      # LVIS es muy grande, no usar cache
    device=0
)
