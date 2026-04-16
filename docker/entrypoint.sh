#!/bin/bash
set -e

echo "════════════════════════════════════════════"
echo "  EZZAOUIA Platform — Starting..."
echo "════════════════════════════════════════════"

# Forcer désactivation SSL ODBC au runtime
export ODBCINI=/etc/odbc.ini
export ODBCSYSINI=/etc/

# Vérifier config ODBC
echo "ODBC Driver config:"
odbcinst -q -d -n "ODBC Driver 18 for SQL Server" 2>/dev/null \
    || echo "Warning: odbcinst check failed"

# Attendre SQL Server (ne pas bloquer si indisponible)
echo "[1/4] Waiting for SQL Server..."
python -c "
import time, pyodbc, os

server   = os.environ.get('DB_SERVER', '')
database = os.environ.get('DB_NAME', '')
user     = os.environ.get('DB_USER', '')
password = os.environ.get('DB_PASSWORD', '')

conn_str = (
    'DRIVER={ODBC Driver 18 for SQL Server};'
    f'SERVER={server};'
    f'DATABASE={database};'
    f'UID={user};'
    f'PWD={password};'
    'Encrypt=no;'
    'TrustServerCertificate=yes;'
    'Connection Timeout=10;'
    'MARS_Connection=yes;'
)

for i in range(30):
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        conn.close()
        print('SQL Server connected!')
        break
    except Exception as e:
        print(f'Attempt {i+1}/30: {e}')
        time.sleep(3)
else:
    print('WARNING: SQL Server unreachable — continuing anyway')
" || true

if [ "$1" = "waitress" ]; then
    # Contrainte projet: ne jamais exécuter migrate automatiquement.
    # Activer explicitement via RUN_MIGRATIONS=1 si nécessaire.
    if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
        echo "[2/4] Running migrations (RUN_MIGRATIONS=1)..."
        python manage.py makemigrations --noinput 2>/dev/null || true
        python manage.py makemigrations accounts  --noinput 2>/dev/null || true
        python manage.py makemigrations chatbot   --noinput 2>/dev/null || true
        python manage.py makemigrations ingestion --noinput 2>/dev/null || true
        python manage.py makemigrations audit     --noinput 2>/dev/null || true

        for attempt in 1 2 3; do
            echo "Migration attempt $attempt/3..."
            python manage.py migrate --run-syncdb && break
            echo "Migration failed, retrying in 5 seconds..."
            sleep 5
        done
    else
        echo "[2/4] Skipping migrations (RUN_MIGRATIONS=${RUN_MIGRATIONS:-0})."
    fi

    # Créer superuser si pas encore créé
    echo "[3/4] Checking superuser..."
    python manage.py shell -c "
from apps.accounts.models import User
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@maretap.tn',
        password='Admin@MARETAP2026',
        role='admin'
    )
    print('Superuser created: admin / Admin@MARETAP2026')
    print('CHANGE THIS PASSWORD IMMEDIATELY!')
else:
    print('Superuser already exists.')
" || true

    # Collecter les fichiers statiques (au runtime pour accès aux volumes)
    echo "[3.5/4] Collecting static files..."
    python manage.py collectstatic --noinput --clear 2>/dev/null || \
    python manage.py collectstatic --noinput || true
else
    echo "[2/4] Skipping migrations/bootstrap for service: $1"
fi

echo "[4/4] Starting service: $1"

# Démarrer le bon service selon la commande
case "$1" in
    waitress)
        echo "Starting Waitress server on port 8000..."
        exec python -c "
from waitress import serve
from config.wsgi import application
print('EZZAOUIA Platform running on http://0.0.0.0:8000')
serve(application, host='0.0.0.0', port=8000, threads=4)
"
        ;;
    celery)
        echo "Starting Celery worker..."
        exec celery -A config worker \
            --loglevel=info \
            --concurrency=2 \
            -E
        ;;
    celery-beat)
        echo "Starting Celery Beat scheduler..."
        exec celery -A config beat \
            --loglevel=info \
            --scheduler django_celery_beat.schedulers:DatabaseScheduler
        ;;
    *)
        exec "$@"
        ;;
esac
