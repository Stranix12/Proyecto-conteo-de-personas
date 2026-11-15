"""Descarga el modelo publicado por OpenCV y verifica su integridad."""
from pathlib import Path
import hashlib
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://huggingface.co/opencv/object_detection_yolox/resolve/main/object_detection_yolox_2022nov.onnx'
target = ROOT / 'models/object_detection_yolox_2022nov.onnx'
target.parent.mkdir(exist_ok=True)
checksum = ROOT / 'models/SHA256SUMS.txt'
expected = checksum.read_text(encoding='utf-8').split()[0] if checksum.exists() else None
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
if target.exists() and expected and digest(target) == expected:
    print('El modelo ya existe y su SHA256 es correcto.')
else:
    temp = target.with_suffix('.download')
    try:
        urllib.request.urlretrieve(URL, temp)
        if expected and digest(temp) != expected:
            raise RuntimeError('El SHA256 no coincide. Se conserva el modelo anterior.')
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)
    print('Modelo YOLOX listo.')
