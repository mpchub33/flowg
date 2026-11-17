import json
import math
import os
import re
import subprocess
import sys
import tempfile
import threading
import uuid
from pathlib import Path

import cv2
from flask import Flask, jsonify, render_template, request, send_file, send_from_directory
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

BASE = Path(__file__).resolve().parent
WORK = Path(tempfile.gettempdir()) / "follow_subject_ui"
WORK.mkdir(parents=True, exist_ok=True)
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024 * 1024


@app.errorhandler(Exception)
def api_error(error):
    api_request = request.path == "/upload" or request.path.startswith("/process/")
    if not api_request:
        if isinstance(error, HTTPException):
            return error
        app.logger.exception("Unhandled request error")
        return "Error interno del servidor", 500
    if isinstance(error, RequestEntityTooLarge):
        return jsonify(error="El video supera el límite de carga del servidor (2 GB). Prueba con un archivo más pequeño."), 413
    if isinstance(error, HTTPException):
        return jsonify(error=error.description), error.code
    app.logger.exception("API request failed")
    return jsonify(error="Error interno del servidor al recibir o procesar el video. Inténtalo de nuevo; si persiste, comparte el identificador del error."), 500


def job_dir(job_id):
    if not re.fullmatch(r"[0-9a-f]{32}", job_id):
        return WORK / "__invalid_job_id__"
    return WORK / job_id


def write_status(folder, data):
    temp = folder / "status.tmp"
    temp.write_text(json.dumps(data, ensure_ascii=False))
    temp.replace(folder / "status.json")


def run_processing(folder, command, expected_frames):
    write_status(folder, {"state": "running", "progress": 1, "message": "Iniciando el detector de personas…",
                          "expected_frames": expected_frames})
    try:
        with (folder / "process.log").open("w", encoding="utf-8", errors="replace") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, text=True, timeout=21600)
        output = folder / "video_vertical.mp4"
        if result.returncode != 0 or not output.exists():
            log_text = (folder / "process.log").read_text(encoding="utf-8", errors="replace")
            detail = log_text[-5000:] or "Error durante el procesamiento."
            if "No module named 'lap'" in detail:
                detail = "Falta el módulo lap requerido por ByteTrack. Instala las dependencias del proyecto (lapx>=0.5.5) y reinicia la app."
            write_status(folder, {"state": "error", "progress": 0, "error": detail})
            return
        write_status(folder, {"state": "done", "progress": 100, "message": "Video listo."})
    except subprocess.TimeoutExpired:
        write_status(folder, {"state": "error", "progress": 0, "error": "El procesamiento superó el límite de 6 horas."})
    except Exception as exc:
        app.logger.exception("Background video processing failed")
        write_status(folder, {"state": "error", "progress": 0, "error": f"Error del servidor durante el procesamiento: {exc}"})


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/manus-routes.json")
def routes_manifest():
    return send_file(BASE / "static" / "manus-routes.json", mimetype="application/json")


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.post("/upload")
def upload():
    f = request.files.get("video")
    if not f or not f.filename:
        return jsonify(error="Selecciona un video."), 400
    job_id = uuid.uuid4().hex
    folder = job_dir(job_id)
    folder.mkdir(parents=True, exist_ok=True)
    suffix = Path(f.filename).suffix.lower() or ".mp4"
    source = folder / f"source{suffix}"
    f.save(source)
    cap = cv2.VideoCapture(str(source))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    duration = frames / fps if fps else 0
    precise_fps = fps if math.isfinite(fps) and 1.0 <= fps <= 240.0 else 30.0
    if duration <= 0 or width <= 0 or height <= 0:
        source.unlink(missing_ok=True)
        folder.rmdir()
        return jsonify(error="No se pudo leer ese video. Prueba con MP4, MOV o WebM."), 400
    return jsonify(id=job_id, name=Path(f.filename).name, duration=duration, fps=precise_fps,
                   width=width, height=height, url=f"/media/{job_id}")


@app.get("/media/<job_id>")
def media(job_id):
    folder = job_dir(job_id)
    matches = list(folder.glob("source.*")) if folder.exists() else []
    if not matches:
        return "Video no encontrado", 404
    return send_file(matches[0], conditional=True)


@app.post("/process/<job_id>")
def process(job_id):
    folder = job_dir(job_id)
    sources = list(folder.glob("source.*")) if folder.exists() else []
    if not sources:
        return jsonify(error="Vuelve a cargar el video."), 404
    try:
        start = float(request.form["start"])
        end = float(request.form["end"])
        x = int(float(request.form["x"]))
        y = int(float(request.form["y"]))
        fill = float(request.form.get("fill", "0.9"))
        sigma = float(request.form.get("sigma", "0.7"))
        zoom = float(request.form.get("zoom", "4"))
        out_h = int(request.form.get("out_h", "1920"))
        duration = float(request.form["duration"])
        if start < 0 or end <= start or end > duration + 0.1:
            raise ValueError("El intervalo de inicio y fin no es válido.")
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify(error=f"Revisa el tramo y el recuadro del sujeto: {exc}"), 400

    cap = cv2.VideoCapture(str(sources[0]))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    cap.release()
    # WebM screen recordings can report a 1/1000 timebase as if it were 1000 FPS.
    # The processor estimates the exact interval FPS from decoded frames; use a
    # conservative value here only for the approximate progress bar.
    if not math.isfinite(fps) or fps < 1.0 or fps > 240.0:
        fps = 25.0
    expected_frames = max(1, math.ceil((end - start) * fps))
    output = folder / "video_vertical.mp4"
    model = os.environ.get("FOLLOW_SUBJECT_MODEL", "yolov8n.pt")
    command = [sys.executable, str(BASE / "follow_subject.py"), str(sources[0]), str(output),
               "--click", f"{x},{y}", "--t0", str(start), "--t1", str(end),
               "--fill", str(fill), "--sigma", str(sigma), "--max-zoom", str(zoom),
               "--out-h", str(out_h), "--model", model]
    write_status(folder, {"state": "queued", "progress": 0, "message": "En cola…",
                          "expected_frames": expected_frames})
    threading.Thread(target=run_processing, args=(folder, command, expected_frames), daemon=True).start()
    return jsonify(task_id=job_id), 202


@app.get("/process/<job_id>/status")
def process_status(job_id):
    folder = job_dir(job_id)
    status_file = folder / "status.json"
    if not status_file.exists():
        return jsonify(error="No se encontró el trabajo. Vuelve a cargar el video."), 404
    data = json.loads(status_file.read_text(encoding="utf-8"))
    if data["state"] == "running":
        log_file = folder / "process.log"
        tail = log_file.read_text(encoding="utf-8", errors="replace")[-12000:] if log_file.exists() else ""
        detect = re.findall(r"detectando (\d+) fotogramas", tail)
        render = re.findall(r"renderizando (\d+) fotogramas", tail)
        if render:
            done = int(render[-1])
            data["progress"] = min(99, 50 + int(49 * done / max(1, data.get("expected_frames", 1))))
            data["message"] = f"Renderizando fotogramas… {done}"
        elif detect:
            done = int(detect[-1])
            data["progress"] = min(49, int(49 * done / max(1, data.get("expected_frames", 1))))
            data["message"] = f"Detectando y siguiendo personas… {done} fotogramas"
        else:
            data["progress"] = max(1, int(data.get("progress", 1)))
            data["message"] = "Cargando el modelo y preparando la detección…"
    elif data["state"] == "done":
        data.update(video_url=f"/result/{job_id}", download_url=f"/download/{job_id}")
    return jsonify(data)


@app.get("/result/<job_id>")
def result_video(job_id):
    output = job_dir(job_id) / "video_vertical.mp4"
    if not output.exists():
        return "Archivo no encontrado", 404
    return send_file(output, mimetype="video/mp4", conditional=True)


@app.get("/download/<job_id>")
def download(job_id):
    output = job_dir(job_id) / "video_vertical.mp4"
    if not output.exists():
        return "Archivo no encontrado", 404
    return send_from_directory(output.parent, output.name, as_attachment=True)


if __name__ == "__main__":
    host = os.environ.get("FOLLOW_SUBJECT_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8501"))
    if os.environ.get("FOLLOW_SUBJECT_OPEN_BROWSER") == "1":
        import threading as timer_threading
        import webbrowser
        timer_threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    app.run(host=host, port=port, threaded=True)
