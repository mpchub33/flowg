# Plan de despliegue — Follow Subject

## Alcance

Publicar sin rediseño la aplicación Flask existente del ZIP. La aplicación permite cargar un video, seleccionar un intervalo y marcar un punto sobre una persona para producir un recorte vertical 9:16 estabilizado mediante Ultralytics YOLO.

## Implementación

- Mantener `app.py`, `follow_subject.py`, `templates/` y `static/` del proyecto entregado.
- Añadir `/healthz` como endpoint público de salud.
- Añadir `static/manus-routes.json` con la única ruta de página `/`.
- Empaquetar el servicio en un contenedor Python 3.11 con FFmpeg, OpenCV, SciPy, Ultralytics, `lapx` y `imageio-ffmpeg`.
- Escuchar en `0.0.0.0` y respetar la variable `PORT`; el runtime administrado usa el puerto 3000.
- Mantener los videos y resultados en el almacenamiento temporal del contenedor, coherente con el flujo actual de la aplicación.

## Estructura

- `app.py`: servidor Flask, carga de videos, trabajos en segundo plano y descarga de resultados.
- `follow_subject.py`: detección, seguimiento, suavizado de cámara virtual y renderizado FFmpeg.
- `templates/index.html`: interfaz web en español.
- `static/`: JavaScript y CSS de la línea de tiempo, además del manifiesto de rutas.
- `Dockerfile`: imagen reproducible para publicación.
- `requirements.txt`: dependencias Python declaradas por el proyecto.

## Diseño conservado

Se conserva el diseño existente de editor visual: superficie clara, acentos verde petróleo, tarjetas de trabajo, controles temporales directos y comparación lado a lado. No se introducen nuevas imágenes ni cambios de marca; la prioridad es preservar el flujo del ZIP.
