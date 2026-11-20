from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    if sys.version_info[:2] != (3, 11):
        raise SystemExit('Instala Python 3.11 para usar las versiones verificadas del proyecto.')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r',
                    str(ROOT / 'requirements.txt')], check=True)
    target = ROOT / '.env'
    if not target.exists():
        config = (ROOT / '.env.example').read_text(encoding='utf-8')
        config = config.replace('change-this-for-a-private-random-value', secrets.token_urlsafe(48))
        config = config.replace('choose-a-local-password', secrets.token_urlsafe(24))
        target.write_text(config, encoding='utf-8')
        print('Se creo .env con claves locales. Para PostgreSQL instalado, ajusta sus datos.')
    subprocess.run([sys.executable, str(ROOT / 'scripts/download_model.py')], check=True)
    print('Preparacion completa. Inicia PostgreSQL o ejecuta docker compose up -d db.')
    print('Despues abre Iniciar.cmd. Consulta README.md para configurar la base.')

if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(f'La preparacion fallo (codigo {error.returncode}). Revisa el mensaje anterior.')
