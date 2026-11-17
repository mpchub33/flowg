#!/usr/bin/env python3
"""
Recorte 9:16 que sigue a UN sujeto (cuerpo completo) con zoom estable.

Uso:
  # 1) detectar + seguir (necesita: pip install ultralytics opencv-python scipy numpy ; ffmpeg instalado)
  python follow_subject.py entrada.webm salida.mp4 --click 640,700 --t0 9
      (--click = un punto sobre el sujeto en el fotograma t0, en pixeles del video original)
      (si omites --click se abre una ventana para dibujar un cuadro sobre el sujeto)

  # 2) solo recortar con cajas ya calculadas
  python follow_subject.py entrada.webm salida.mp4 --boxes cajas.json

Opciones utiles:
  --fill 0.90     el cuerpo ocupa 90% del alto del cuadro 9:16
  --sigma 0.7     segundos de suavizado (mas alto = camara mas "pesada" y estable)
  --out-h 1920    alto de salida (1080x1920 por defecto)
  --max-zoom 4    limite de zoom para no pixelar demasiado
"""
import argparse, json, subprocess, sys, shutil
from fractions import Fraction
import cv2, numpy as np
from scipy.ndimage import gaussian_filter1d, median_filter

FPS = 25.0

def get_ffmpeg():
    if shutil.which('ffmpeg'):
        return 'ffmpeg'
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return 'ffmpeg'

FFMPEG_BIN = get_ffmpeg()


def probe(path):
    if shutil.which('ffprobe'):
        try:
            out = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                                           '-show_entries', 'stream=width,height,avg_frame_rate,r_frame_rate',
                                           '-of', 'json', path]).decode()
            stream = json.loads(out)['streams'][0]
            fps = 0.0
            for rate in (stream.get('avg_frame_rate'), stream.get('r_frame_rate')):
                try:
                    fps = float(Fraction(rate)) if rate else 0.0
                    if 1.0 <= fps <= 240.0:
                        break
                except (ValueError, ZeroDivisionError):
                    fps = 0.0
            if not (1.0 <= fps <= 240.0):
                fps = 25.0
            return int(stream['width']), int(stream['height']), fps
        except Exception:
            pass
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el video: {path}")
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    return w, h, fps if 1.0 <= fps <= 240.0 else 25.0


def frames(path, w, h, t0=0.0, t1=None):
    cmd = [FFMPEG_BIN, '-v', 'error', '-ss', str(t0)]
    if t1 is not None:
        cmd += ['-t', str(max(0.0, t1 - t0))]
    # Decode every source frame. Do not apply an fps filter that can drop frames.
    cmd += ['-i', path, '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = w * h * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        yield np.frombuffer(buf, np.uint8).reshape(h, w, 3)
    p.wait()


# ---------- apariencia (re-identificacion por color de ropa) ----------
def hist(img, b):
    x1, y1, x2, y2 = [int(v) for v in b]
    w, h = x2 - x1, y2 - y1
    H, W = img.shape[:2]
    xa, xb = max(0, x1 + int(w * .2)), min(W, x2 - int(w * .2))
    ya, yb = max(0, y1 + int(h * .1)), min(H, y1 + int(h * .7))
    if xb - xa < 4 or yb - ya < 4:
        return None
    hsv = cv2.cvtColor(img[ya:yb, xa:xb], cv2.COLOR_BGR2HSV)
    hs = cv2.calcHist([hsv], [0, 1], None, [18, 8], [0, 180, 0, 256])
    cv2.normalize(hs, hs, 1, 0, cv2.NORM_L1)
    return hs


def dist(a, b):
    return 1.0 if a is None or b is None else cv2.compareHist(a, b, cv2.HISTCMP_BHATTACHARYYA)


# ---------- etapa 1: detectar y seguir ----------
def detect(args, w, h):
    from ultralytics import YOLO
    model = YOLO(args.model)
    gen = frames(args.inp, w, h, args.t0, args.t1)
    first = next(gen)
    if args.click:
        cx, cy = [int(v) for v in args.click.split(',')]
    else:
        r = cv2.selectROI('Dibuja un cuadro sobre el sujeto y pulsa ENTER', first)
        cv2.destroyAllWindows()
        cx, cy = int(r[0] + r[2] / 2), int(r[1] + r[3] / 2)

    track_id, ref, res = None, None, []
    t = args.t0
    for i, f in enumerate(__import__('itertools').chain([first], gen)):
        r = model.track(f, persist=True, classes=[0], conf=0.3, verbose=False, tracker='bytetrack.yaml')[0]
        boxes = r.boxes.xyxy.cpu().numpy() if r.boxes is not None else np.zeros((0, 4))
        ids = r.boxes.id.cpu().numpy().astype(int) if r.boxes is not None and r.boxes.id is not None else \
            -np.ones(len(boxes), int)
        pick = None
        if i == 0:   # eleccion inicial: la caja que contiene el punto (la mas pequena)
            c = [k for k, b in enumerate(boxes) if b[0] <= cx <= b[2] and b[1] <= cy <= b[3]]
            if c:
                pick = min(c, key=lambda k: (boxes[k][2] - boxes[k][0]) * (boxes[k][3] - boxes[k][1]))
                track_id, ref = ids[pick], hist(f, boxes[pick])
        else:
            m = [k for k in range(len(boxes)) if ids[k] == track_id and track_id != -1]
            if m:
                pick = m[0]
                if dist(ref, hist(f, boxes[pick])) < 0.35:           # adapta apariencia despacio
                    ref = 0.97 * ref + 0.03 * hist(f, boxes[pick])
            elif len(boxes):                                          # perdido: re-identifica por color
                ds = [dist(ref, hist(f, b)) for b in boxes]
                k = int(np.argmin(ds))
                if ds[k] < 0.40:
                    pick, track_id = k, ids[k]
        res.append({'t': round(t, 3), 'box': boxes[pick].tolist() if pick is not None else None})
        t += 1 / FPS
        if i % 250 == 0:
            print(f'detectando {i} fotogramas...', file=sys.stderr)
    json.dump(res, open(args.save_boxes, 'w'))
    return res


# ---------- etapa 2: camara virtual estable ----------
def plan_camera(res, w, h, a):
    n = len(res)
    arr = np.full((n, 4), np.nan)
    for i, r in enumerate(res):
        if r['box'] is not None:
            arr[i] = r['box']
    ok = ~np.isnan(arr[:, 0])
    if ok.sum() < 2:
        sys.exit('No se encontro al sujeto.')
    idx = np.arange(n)
    for c in range(4):                       # rellena huecos
        arr[:, c] = np.interp(idx, idx[ok], arr[ok, c])
    cx = (arr[:, 0] + arr[:, 2]) / 2
    cy = (arr[:, 1] + arr[:, 3]) / 2
    bh = np.maximum(arr[:, 3] - arr[:, 1], 20)
    # quita saltos sueltos y suaviza (offline => filtro no causal, sin retraso)
    sig = a.sigma * FPS
    cx, cy = [gaussian_filter1d(median_filter(v, 9, mode='nearest'), sig, mode='nearest') for v in (cx, cy)]
    lbh = gaussian_filter1d(median_filter(np.log(bh), 9, mode='nearest'), sig * 1.6, mode='nearest')
    ch = np.exp(lbh) / a.fill                # alto del recorte
    ch = np.clip(ch, h / a.max_zoom, h)
    cw = ch * 9 / 16
    over = cw > w                            # si el video es mas estrecho que 9:16
    ch[over], cw[over] = w * 16 / 9, w
    cx = np.clip(cx, cw / 2, w - cw / 2)
    cy = np.clip(cy, ch / 2, h - ch / 2)
    return cx, cy, cw, ch


def render(args, w, h, cx, cy, cw, ch, t0):
    ow = int(round(args.out_h * 9 / 16 / 2)) * 2
    cmd = [FFMPEG_BIN, '-v', 'error', '-y',
           '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{ow}x{args.out_h}', '-r', str(FPS), '-i', '-',
           '-ss', str(t0)]
    if args.t1 is not None:
        cmd += ['-t', str(max(0.0, args.t1 - t0))]
    cmd += ['-i', args.inp, '-map', '0:v', '-map', '1:a?',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '15', '-pix_fmt', 'yuv420p',
           '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-shortest', args.out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i, f in enumerate(frames(args.inp, w, h, t0, args.t1)):
        if i >= len(cx):
            break
        if i % 250 == 0:
            print(f'renderizando {i} fotogramas...', file=sys.stderr)
        s = args.out_h / ch[i]
        # recorte con sub-pixel (afin) => sin saltos de 1 pixel
        M = np.array([[s, 0, ow / 2 - cx[i] * s], [0, s, args.out_h / 2 - cy[i] * s]], np.float32)
        o = cv2.warpAffine(f, M, (ow, args.out_h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        p.stdin.write(o.tobytes())
    p.stdin.close()
    p.wait()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('inp'); ap.add_argument('out')
    ap.add_argument('--click'); ap.add_argument('--boxes')
    ap.add_argument('--t0', type=float, default=0.0); ap.add_argument('--t1', type=float)
    ap.add_argument('--fill', type=float, default=0.90)
    ap.add_argument('--sigma', type=float, default=0.7)
    ap.add_argument('--max-zoom', type=float, default=4.0)
    ap.add_argument('--out-h', type=int, choices=[0, 1080, 1920], default=0,
                    help='0 = automático sin ampliar la resolución nativa; 1080 o 1920 = altura de salida fija')
    ap.add_argument('--model', default='yolov8m.pt')
    ap.add_argument('--save-boxes', default='cajas.json')
    a = ap.parse_args()
    W, H, FPS = probe(a.inp)
    if a.out_h == 0:
        # Largest 9:16 crop that fits inside the source frame, rounded to an even dimension.
        native_crop_h = min(H, W * 16 / 9)
        a.out_h = max(2, int(native_crop_h) // 2 * 2)
    res = json.load(open(a.boxes)) if a.boxes else detect(a, W, H)
    t_start = res[0]['t']
    if a.t1 is not None and a.t1 > t_start and res:
        # Some WebM recordings have avg_frame_rate=0/0 and r_frame_rate=1000/1.
        # In that case probe() must fall back for decoding, but encoding all the
        # selected frames at that fallback rate changes playback speed. Estimate
        # the actual average rate of this exact interval so its output duration
        # matches the user's selected duration.
        FPS = len(res) / (a.t1 - t_start)
        print(f'FPS efectivo del tramo: {FPS:.3f} ({len(res)} fotogramas)', file=sys.stderr)
    cx, cy, cw, ch = plan_camera(res, W, H, a)
    render(a, W, H, cx, cy, cw, ch, t_start)
    print('listo ->', a.out)
