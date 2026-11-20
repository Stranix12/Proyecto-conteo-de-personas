"""Inicia PostgreSQL portátil de este equipo si está disponible y ejecuta Django.

En otro equipo utiliza PostgreSQL instalado o compose.yaml. No distribuye
credenciales ni descarga binarios del servidor de base de datos.
"""
from pathlib import Path
import os, subprocess, sys, socket
import psycopg

ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if not (ROOT/'.env').exists():
    raise SystemExit('Primero crea .env a partir de .env.example y configura PostgreSQL. Consulta README.md.')
from dotenv import load_dotenv
load_dotenv(ROOT/'.env')
if '--check' not in sys.argv:
    with socket.socket() as server_socket:
        try:
            server_socket.bind(('127.0.0.1', 8000))
        except OSError:
            raise SystemExit('El puerto 8000 ya esta ocupado. Abre http://127.0.0.1:8000/ o detén la otra instancia.')
host=os.environ.get('DB_HOST','127.0.0.1')
port=int(os.environ.get('DB_PORT','55432'))
os.environ.setdefault('PGCONNECT_TIMEOUT', '5')
print('Comprobando PostgreSQL...', flush=True)
try:
    with socket.create_connection((host,port),timeout=1):pass
except OSError:
    work=ROOT.parent.parent/'work'
    pg=work/'postgres/pgsql/bin/pg_ctl.exe'
    data=work/'pgdata'
    if not pg.exists() or not (data/'PG_VERSION').exists():
        raise SystemExit('PostgreSQL no está disponible. Inicia tu servidor o ejecuta docker compose up -d db.')

    options = {}
    if os.name == 'nt':
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        options = {'creationflags': subprocess.CREATE_NEW_CONSOLE, 'startupinfo': startup}
    subprocess.run([str(pg),'-D',str(data),'-l',str(work/'postgres.log'),'-w','start'],check=True, **options)
try:
    with psycopg.connect(host=host, port=port,
                         dbname=os.environ.get('DB_NAME', 'conteo_personas'),
                         user=os.environ.get('DB_USER', 'conteo'),
                         password=os.environ.get('DB_PASSWORD', ''),
                         connect_timeout=5) as connection:
        connection.execute('SELECT 1')
except psycopg.Error:
    raise SystemExit('PostgreSQL no responde o la configuración de .env es incorrecta. Revisa la base antes de volver a iniciar; no abras varias instancias.')
subprocess.run([sys.executable,'manage.py','migrate'],check=True)
subprocess.run([sys.executable, str(ROOT/'scripts/download_model.py')], check=True)
subprocess.run([sys.executable,'manage.py','check'],check=True)
if '--check' in sys.argv:
    print('Configuracion, base y modelo verificados.', flush=True)
    raise SystemExit(0)
print('Abre http://127.0.0.1:8000/ en el navegador. Ctrl+C para detener Django.',flush=True)
subprocess.run([sys.executable,'manage.py','runserver','127.0.0.1:8000','--noreload'],check=True)
