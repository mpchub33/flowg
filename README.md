# Follow Subject — editor visual para tu PC

Abre un video en el navegador, selecciona el intervalo con la regla temporal, el zoom y sus tiradores, arrastra el cursor de reproducción o avanza por fotogramas con el teclado, dibuja un recuadro sobre la persona y procesa solo ese tramo. El resultado se compara en paralelo con el original.

La salida predeterminada evita ampliar la resolución nativa del recorte, conserva todos los fotogramas y ajusta el FPS efectivo al tramo elegido para mantener su duración y velocidad, incluidos videos WebM con FPS variables o metadatos incompletos. Codifica en H.264 con CRF 15/preset medio. El recorte vertical requiere volver a codificar, por lo que la compresión y el tamaño no serán idénticos al archivo original.

## Windows

1. Descomprime todo el ZIP en una carpeta local.
2. Haz doble clic en `INSTALAR_Y_ABRIR.bat`. Comprueba si está el lanzador `py`, instala Python 3.11 si hace falta y prepara la app.
3. Espera a que descargue Python (si hace falta) y los paquetes. La primera instalación puede tardar varios minutos y descargar PyTorch.
4. Se abrirá `http://127.0.0.1:8501`. Deja abierta la ventana negra mientras usas la app.

El ZIP incluye un iniciador `.bat`, no un instalador MSI/EXE firmado. Para instalar Python automáticamente, Windows necesita el lanzador `py` (Python Install Manager); si no lo tienes, instala primero Python 3.11 de 64 bits desde python.org.

## macOS o Linux

Instala Python 3.10 o 3.11 y descomprime el ZIP. En Terminal, ejecuta:

```bash
cd follow-subject-app
chmod +x iniciar_mac_linux.sh
./iniciar_mac_linux.sh
```

La app abrirá `http://127.0.0.1:8501` si el sistema puede abrir el navegador automáticamente.

## GPU

Los iniciadores ejecutan `comprobar_gpu.py`. Si muestra una GPU CUDA, YOLO la puede usar automáticamente. Si indica CPU, la app seguirá funcionando, pero el análisis de videos largos puede tardar mucho. La aceleración CUDA requiere una GPU NVIDIA y una instalación de PyTorch compatible con los controladores; no todas las GPU aceleran este modelo.

El video se procesa en tu computadora y el servidor escucha solo en `127.0.0.1` cuando se inicia con los archivos incluidos, así que no se publica en Internet. No cierres la ventana del servidor durante el procesamiento. La primera ejecución también puede descargar el modelo YOLO. El valor predeterminado es `yolov8n.pt`, que reduce el consumo de memoria en servicios cloud; puedes usar otro archivo definiendo `FOLLOW_SUBJECT_MODEL`.

## Requisitos / solución de problemas

- Python 3.11 de 64 bits recomendado en Windows.
- Conexión a Internet durante la primera instalación y para descargar los pesos YOLO.
- El equipo requiere espacio libre para el entorno Python, el modelo y los videos temporales.
- Si el puerto 8501 está ocupado, cierra la otra app Follow Subject antes de iniciar esta.
- Para detener el servidor, vuelve a la ventana de terminal y pulsa `Ctrl+C`.

## Desarrollo o servidor propio

Instala `requirements.txt` dentro de un entorno virtual y ejecuta `python app.py`. Por defecto, el host es `0.0.0.0` para permitir el proxy del entorno de despliegue; los iniciadores locales incluidos fijan `FOLLOW_SUBJECT_HOST=127.0.0.1`.
