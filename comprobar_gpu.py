try:
    import torch
except ImportError:
    print("PyTorch aún no está instalado. Ejecuta primero el iniciador del sistema.")
    raise SystemExit(1)

print("PyTorch:", torch.__version__)
if torch.cuda.is_available():
    print("GPU CUDA disponible:", torch.cuda.get_device_name(0))
    print("YOLO podrá utilizar CUDA automáticamente.")
else:
    print("No se detectó CUDA; el procesamiento usará CPU.")
    print("Para CUDA se requiere una GPU NVIDIA, controladores compatibles y una versión de PyTorch con CUDA.")
