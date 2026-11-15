"""Inicia PostgreSQL portátil de este equipo si está disponible y ejecuta Django.

En otro equipo utiliza PostgreSQL instalado o compose.yaml. No distribuye
credenciales ni descarga binarios del servidor de base de datos.
"""
from pathlib import Path
import os, subprocess, sys, socket

ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if not (ROOT/'.env').exists():
    raise SystemExit('Primero crea .env a partir de .env.example y configura PostgreSQL. Consulta README.md.')
from dotenv import load_dotenv
load_dotenv(ROOT/'.env')
host=os.environ.get('DB_HOST','127.0.0.1')
port=int(os.environ.get('DB_PORT','55432'))
try:
    with socket.create_connection((host,port),timeout=1):pass
except OSError:
    work=ROOT.parent.parent/'work'
    pg=work/'postgres/pgsql/bin/pg_ctl.exe'
    data=work/'pgdata'
    if not pg.exists() or not (data/'PG_VERSION').exists():
        raise SystemExit('PostgreSQL no está disponible. Inicia tu servidor o ejecuta docker compose up -d db.')
    subprocess.run([str(pg),'-D',str(data),'-l',str(work/'postgres.log'),'-w','start'],check=True)
subprocess.run([sys.executable,'manage.py','migrate'],check=True)
print('Abre http://127.0.0.1:8000/ en el navegador. Ctrl+C para detener Django.',flush=True)
subprocess.run([sys.executable,'manage.py','runserver','127.0.0.1:8000','--noreload'],check=True)
