# LabCount

Aplicación web para contar personas visibles en imágenes o video mediante
**Django, OpenCV DNN, YOLOX y PostgreSQL**. Proyecto de la práctica 03 de
Construcción de Software. El desarrollo está organizado para abrirse en
**Visual Studio Code**.

## Empezar en este computador

1. Abre esta carpeta en Visual Studio Code con **File > Open Folder**.
2. Abre `docs/informe.md` para consultar el proceso completo y los cambios.
3. Ejecuta `Iniciar.cmd` desde el Explorador de Windows. Usa el entorno `.venv`
   ya configurado e inicia el PostgreSQL portátil de esta carpeta de trabajo.
4. Entra a **http://127.0.0.1:8000/** y pulsa **Probar ejemplo**.
5. Para trabajar desde VS Code, selecciona el intérprete
   `.venv\Scripts\python.exe`. En **Terminal > Run Task** están disponibles
   `LabCount iniciar`, `LabCount pruebas` y `LabCount migrar`.
6. Con las extensiones Python y Python Debugger instaladas, F5 permite usar
   la configuración `LabCount Django`. Inicia antes PostgreSQL. Si ya hay un
   servidor en el puerto 8000, detenlo antes de lanzar otra instancia.

Si VS Code muestra modo restringido, el código puede inspeccionarse sin
alterar esa configuración. La ejecución de tareas/extensiones depende de
la configuración de confianza que el propietario del equipo decida usar.

## Instalar en otro computador con Windows

Requisitos: Python 3.11, PostgreSQL 17 o Docker Desktop con Compose, VS Code
y navegador con soporte de cámara y video H.264. El proyecto no necesita GPU.
Los siguientes comandos se ejecutan en la terminal desde la raíz del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `.env` en VS Code. Define una contraseña propia para `DB_PASSWORD` y una
clave aleatoria privada para `SECRET_KEY`. No publiques este archivo. El
puerto de conexión configurado es **55432**.

Opción A, servidor instalado: crea el usuario y la base con pgAdmin o psql
y usa sus credenciales en `.env`. Para las pruebas de Django, el usuario
necesita permiso `CREATEDB` para crear `test_conteo_personas`.

```sql
CREATE ROLE conteo LOGIN PASSWORD 'tu_clave_local' CREATEDB;
CREATE DATABASE conteo_personas OWNER conteo;
```

Opción B, Docker, con las mismas variables de `.env`:

```powershell
docker compose up -d db
```

Después de que PostgreSQL esté disponible:

```powershell
.\.venv\Scripts\python.exe scripts\download_model.py
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test counter --verbosity 2
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
```

`scripts/download_model.py` verifica SHA256 y solo descarga si el modelo falta
o no coincide. El ZIP de entrega ya contiene el ONNX. El proyecto no incluye
entorno virtual, credenciales ni datos de PostgreSQL en el paquete fuente.

## Usar el sistema

* **Ejemplo:** procesa la imagen pública de OpenCV con dos personas.
* **Cámara:** selecciona la cámara del computador, inicia el conteo y concede
  el permiso en tu navegador. Se usa video sin micrófono. No es necesario
  conceder acceso a la cámara para probar imágenes o archivos de video.
* **Video:** selecciona Archivo de video y carga un MP4 compatible. Para
  comprobar el flujo usa `docs/video_prueba.mp4`, que repite una imagen e
  intercala cuadros negros; no es una escena real del laboratorio.
* **Imagen:** carga una imagen. Se procesa una vez y se cierra la sesión.
* **Aforo:** admite enteros entre 1 y 1000; se inicia con 24 personas.
* **Umbral:** 0.35 por defecto; subirlo exige mayor puntuación de detección.
  La puntuación del modelo no constituye una probabilidad calibrada.
* **Detener:** libera la cámara o el video y cierra la sesión.
* **Historial:** presenta las 30 sesiones más recientes del mismo navegador,
  su máximo, promedio y número de imágenes procesadas.
* **Exportar CSV:** descarga todas las lecturas de ese navegador, incluyendo
  fecha de Ecuador, conteo, aforo, umbral y tiempo de procesamiento.

## Qué representa el conteo

Se cuenta la clase COCO **persona por imagen** después de eliminar recuadros
redundantes con NMS. Dos imágenes con la misma persona producen dos lecturas,
no dos visitantes. No hay seguimiento, identificación facial, registro de
asistencia ni acumulación de entradas y salidas. La ocupación porcentual se
calcula como `personas / aforo * 100`; puede superar 100 % y dispara una alerta.

La cámara y el archivo de video se reproducen de forma continua en un elemento
de video nativo. Los recuadros se dibujan en una capa SVG independiente y se
actualizan al recibir una detección. Un resultado lento no frena la reproducción.
La cámara solicita hasta 30 FPS; la frecuencia real depende del dispositivo y
del navegador. Los recuadros se retiran si pasan 1.2 segundos sin actualizarse.

El navegador toma muestras JPEG con un intervalo objetivo mínimo de 250 ms
entre inicios de detección, hasta cuatro por segundo si el equipo lo permite.
Solo se admite una inferencia pendiente; si tarda más, la siguiente espera.
La fluidez del video no implica que cada fotograma se analice. Al detener,
se muestra la última imagen anotada como referencia, con la sesión ya detenida.

## Estructura

```text
.vscode/          configuraciones de ejecución y tareas de VS Code
config/           configuración Django y rutas
counter/          modelos, API, detector, interfaz, migraciones y pruebas
models/           modelo ONNX, licencia y SHA256
scripts/          inicio local y descarga/verificación del modelo
docs/             informe editable, bitácora, evidencias y videos
manage.py         comandos administrativos Django
requirements.txt  versiones verificadas
compose.yaml      alternativa PostgreSQL con Docker
```

## Verificación realizada

Se aprobaron **22 pruebas** con PostgreSQL real. La salida se conserva en
`docs/evidencias/pruebas_automatizadas.txt`. Además pasaron nueve pruebas JavaScript
que cubren video continuo, superposición, caducidad, cierre y concurrencia.


## Datos y ejecución

El servidor escucha solo en `127.0.0.1`. La configuración `DEBUG=1` es para
desarrollo local. No se guardan fotogramas de los usuarios: PostgreSQL conserva
sesiones y lecturas numéricas. 

