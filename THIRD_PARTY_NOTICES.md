# Componentes de terceros

El código de la aplicación integra un modelo preentrenado y una imagen de
ejemplo. No se atribuye la autoría del modelo ni de la imagen al equipo.

* **YOLOX de OpenCV Zoo**: modelo `object_detection_yolox_2022nov.onnx`,
  distribuido por OpenCV. Licencia Apache 2.0 conservada en
  `models/LICENSE-YOLOX.txt`. Fuente:
  https://github.com/opencv/opencv_zoo/tree/main/models/object_detection_yolox
  Descarga: https://huggingface.co/opencv/object_detection_yolox
* **Imagen basketball1.png**: archivo de ejemplo de OpenCV 4.12.0.
  Fuente: https://github.com/opencv/opencv/blob/4.12.0/samples/data/basketball1.png
  Licencia de la distribución conservada en
  `counter/static/counter/LICENSE-sample.txt`.
* El preprocesamiento y la decodificación YOLOX siguen la especificación del
  ejemplo oficial de OpenCV Zoo. La aplicación filtra exclusivamente la clase
  COCO persona, aplica NMS y dibuja los resultados con OpenCV.
* Django, OpenCV, NumPy, Psycopg y python-dotenv se instalan desde PyPI y
  conservan sus licencias de distribución en sus paquetes.

El video de prueba repite la imagen de OpenCV e incluye segmentos negros.
Es material controlado para comprobar el flujo; no representa una grabación
real de un laboratorio.
