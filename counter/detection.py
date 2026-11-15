"""Conteo de personas con YOLOX ONNX ejecutado mediante OpenCV DNN.

El modelo preentrenado de OpenCV Zoo detecta clases COCO. Se conserva
solamente la clase persona. No se realiza identificación de individuos.
"""
from pathlib import Path
import threading
import time
import cv2
import numpy as np

MODEL = Path(__file__).resolve().parents[1] / 'models/object_detection_yolox_2022nov.onnx'
_local = threading.local()
_grids, _strides = [], []
for stride in (8, 16, 32):
    y, x = np.mgrid[:640 // stride, :640 // stride]
    _grids.append(np.stack((x, y), axis=-1).reshape(-1, 2))
    _strides.append(np.full((x.size, 1), stride))
GRIDS = np.concatenate(_grids).astype(np.float32)
STRIDES = np.concatenate(_strides).astype(np.float32)


def detector():
    if not MODEL.is_file():
        raise RuntimeError('Falta el modelo YOLOX. Ejecuta python scripts/download_model.py.')
    # La red mantiene buffers internos: una instancia por hilo.
    if not hasattr(_local, 'net'):
        _local.net = cv2.dnn.readNetFromONNX(str(MODEL))
        _local.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        _local.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    return _local.net


def suppress(boxes, scores, threshold=0.35):
    if not len(boxes):
        return []
    indices = cv2.dnn.NMSBoxes(
        [list(map(float, b)) for b in boxes],
        [float(s) for s in scores], threshold, 0.45
    )
    return [int(i) for i in np.asarray(indices).reshape(-1)]


def analyze(raw, threshold=0.35):
    start = time.perf_counter()
    image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError('El archivo no contiene una imagen válida.')
    h, w = image.shape[:2]
    if min(h, w) < 64 or max(h, w) > 4096:
        raise ValueError('Usa imágenes entre 64 y 4096 píxeles por lado.')
    scale = min(1.0, 800 / w, 600 / h)
    if scale < 1:
        image = cv2.resize(image, (round(w * scale), round(h * scale)))
    ih, iw = image.shape[:2]
    ratio = min(640 / iw, 640 / ih)
    # Letterbox: mantiene proporciones y rellena los bordes inferior y derecho.
    padded = np.full((640, 640, 3), 114, dtype=np.float32)
    resized = cv2.resize(
        cv2.cvtColor(image, cv2.COLOR_BGR2RGB),
        (int(iw * ratio), int(ih * ratio))
    )
    padded[:resized.shape[0], :resized.shape[1]] = resized
    net = detector()
    net.setInput(np.transpose(padded, (2, 0, 1))[None])
    output = net.forward()[0]
    centers = (output[:, :2] + GRIDS) * STRIDES
    sizes = np.exp(output[:, 2:4]) * STRIDES
    all_scores = output[:, 4:5] * output[:, 5:]
    classes = all_scores.argmax(axis=1)
    person_scores = all_scores[:, 0]
    keep = (classes == 0) & (person_scores >= threshold)
    boxes = np.concatenate((centers - sizes / 2, sizes), axis=1)[keep] / ratio
    scores = person_scores[keep]
    selected = suppress(boxes, scores, threshold)
    result = []
    for i in selected:
        x, y, bw, bh = boxes[i]
        right = min(iw, round(float(x + bw)))
        bottom = min(ih, round(float(y + bh)))
        x, y = max(0, round(float(x))), max(0, round(float(y)))
        if right <= x or bottom <= y:
            continue
        result.append({
            'x': x, 'y': y, 'width': right - x, 'height': bottom - y,
            'score': round(float(scores[i]), 3)
        })
        cv2.rectangle(image, (x, y), (right, bottom), (100, 235, 60), 2)
        cv2.putText(image, f'Persona {scores[i]:.2f}', (x, max(18, y - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 235, 60), 1)
    cv2.rectangle(image, (0, 0), (250, 34), (28, 31, 23), -1)
    cv2.putText(image, f'Personas detectadas: {len(result)}', (10, 23),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    ok, encoded = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 82])
    if not ok:
        raise ValueError('No se pudo codificar el resultado.')
    return {
        'count': len(result), 'boxes': result,
        'processing_ms': round((time.perf_counter() - start) * 1000, 1),
        'jpeg': encoded.tobytes()
    }
