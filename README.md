# LabCount

Aplicación web para contar personas visibles en imágenes o video mediante
**Django, OpenCV DNN, YOLOX y PostgreSQL**. Proyecto de la práctica 03 de
Construcción de Software. El desarrollo está organizado para abrirse en
**Visual Studio Code**.

## Requisitos para ejecutar en otro computador

- Windows 10/11 de 64 bits y Python 3.11 con el lanzador `py` y pip.
- PostgreSQL 17 instalado **o** Docker Desktop en ejecución con Compose.
- Internet durante la preparación para descargar dependencias y, si falta, el modelo.
- Un navegador actualizado. La cámara es opcional; también se admiten imágenes y videos.
- Visual Studio Code es opcional para iniciar. Para desarrollar, instala las extensiones Python y Python Debugger y selecciona `.venv\Scripts\python.exe` como intérprete.
- Node.js 20 o posterior solo para las pruebas JavaScript. No hace falta para ejecutar Django.

Las bibliotecas están fijadas en `requirements.txt`. La inferencia funciona en CPU.
El repositorio no incluye entorno virtual, credenciales ni datos de PostgreSQL.

## Primera instalación

1. Descarga **Code > Download ZIP**, extráelo y abre la carpeta que contiene `manage.py`. No ejecutes los archivos dentro del ZIP.
2. Ejecuta **Preparar.cmd**. Crea `.venv`, instala las bibliotecas, genera `.env` con claves locales si no existe y verifica o descarga YOLOX. No sobrescribe un `.env` existente. Si falla, muestra el error; corrígelo y vuelve a ejecutar la preparación.
3. Configura una de las dos alternativas de base de datos siguientes.
4. Ejecuta **Iniciar.cmd** y entra a **http://127.0.0.1:8000/**. El inicio comprueba PostgreSQL, aplica migraciones y verifica el modelo antes de levantar Django.

### Alternativa A con Docker

Con Docker Desktop iniciado, abre una terminal en la carpeta del proyecto:

```powershell
docker compose up -d db
```

Espera a que la base esté lista y ejecuta `Iniciar.cmd`. Mantén los valores
predeterminados de `.env` para esta alternativa: host `127.0.0.1`, puerto
`55432`, usuario `conteo` y base `conteo_personas`. Compose utiliza la contraseña
generada por `Preparar.cmd`. Si ya existe un volumen de datos, cambiar la
contraseña en `.env` no cambia la contraseña de ese volumen.

### Alternativa B con PostgreSQL instalado

Crea una base y un usuario desde pgAdmin o psql con una cuenta administradora:

```sql
CREATE ROLE conteo LOGIN PASSWORD 'reemplaza_con_tu_clave';
CREATE DATABASE conteo_personas OWNER conteo;
```

Edita `.env`: pon esa contraseña en `DB_PASSWORD` y el puerto real de PostgreSQL
en `DB_PORT` (habitualmente `5432` en una instalación estándar). Conserva
`DB_NAME=conteo_personas`, `DB_USER=conteo` y `DB_HOST=127.0.0.1`.
Inicia el servicio de PostgreSQL antes de abrir `Iniciar.cmd`.
Para las pruebas de integración que crean una base temporal, un administrador
debe conceder `ALTER ROLE conteo CREATEDB;` en el entorno de desarrollo.

## Uso diario y problemas de inicio

Una vez preparado, inicia PostgreSQL o Docker y abre **Iniciar.cmd**.
No hace falta volver a instalar las bibliotecas cada vez. Cuando cambie
`requirements.txt`, vuelve a ejecutar `Preparar.cmd`.
En VS Code también puedes usar **Terminal > Run Task > LabCount iniciar**.

- Si falta Python, instala la versión 3.11 con su lanzador `py`.
- Si falta `.venv` o alguna biblioteca, ejecuta `Preparar.cmd`.
- Si PostgreSQL no responde, revisa el servicio, el puerto y las credenciales de `.env`. El arranque usa un tiempo límite de conexión; no abras varias instancias mientras solucionas la conexión.
- Si el puerto 8000 está ocupado, comprueba si LabCount ya está abierto y detén la instancia anterior si corresponde.
- No necesitas activar `Activate.ps1` ni cambiar la política de PowerShell. Los comandos usan directamente el Python de `.venv`.
- Detén Django con Ctrl+C. Para detener la base Docker usa `docker compose stop db`; no borres el volumen si quieres conservar el historial.

La detección automática del PostgreSQL portátil es solo una compatibilidad con
el equipo original. Los demás equipos pueden usar cualquiera de las dos
alternativas anteriores sin tener esa carpeta.

## Pruebas de la práctica 4

```powershell
.\.venv\Scripts\python.exe manage.py test counter.test_integrante1 --verbosity 2
node --test tests/ocupacion_integrante1.test.cjs
```

Estas 13 pruebas verifican NMS, umbral, clase persona, aforo y ocupación con
datos controlados; no necesitan una base de datos ni cámara. El código está
en `counter/test_integrante1.py` y `tests/ocupacion_integrante1.test.cjs`.
Los logs y capturas están en `docs/practica4_integrante1/`.

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

