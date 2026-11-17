# Follow Subject — entregables

- [x] La interfaz existente de Follow Subject se sirve desde `/` y conserva su flujo de carga, edición temporal, marcado de persona, procesamiento y descarga. Verificado con una respuesta HTTP 200 y la interfaz HTML esperada.
- [x] La aplicación se ejecuta en un contenedor reproducible con Python, FFmpeg y todas las dependencias de `requirements.txt`. Declarado en `Dockerfile`, incluyendo Gunicorn para producción.
- [x] El servidor escucha en `0.0.0.0` y usa `PORT`, con puerto de runtime administrado 3000. Verificado en Preview con Flask escuchando en `0.0.0.0:3000`.
- [x] Existe un endpoint HTTP público `/healthz` que responde correctamente sin autenticación para la supervisión del despliegue. Verificado con `{"status":"ok"}`.
- [x] El manifiesto `/manus-routes.json` declara la ruta de página `/`. Verificado con HTTP 200 y JSON válido.
- [ ] La versión entregada queda guardada en un checkpoint de `origin/main`; el commit actual es `f5405c2a8647e5032d62723a56f1db8eef4d5e69`. La publicación queda pendiente de confirmación del servicio.
