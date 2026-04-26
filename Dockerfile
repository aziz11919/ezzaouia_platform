FROM python:3.12-slim

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    unixodbc \
    unixodbc-dev \
    curl \
    gnupg \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-ara \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Installer Microsoft ODBC Driver 18 pour SQL Server
RUN apt-get update \
    && apt-get install -y apt-transport-https ca-certificates \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor \
        | tee /usr/share/keyrings/microsoft-prod.gpg > /dev/null \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] \
        https://packages.microsoft.com/debian/12/prod bookworm main" \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y DEBIAN_FRONTEND=noninteractive \
        apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Forcer désactivation SSL — Driver 18 active Encrypt=yes par défaut
ENV ODBCSYSINI=/etc/
ENV ODBCINI=/etc/odbc.ini

# Réécrire odbcinst.ini avec le bon chemin de driver (trouvé dynamiquement)
RUN DRIVER_PATH=$(find /opt/microsoft -name "libmsodbcsql*.so*" 2>/dev/null | sort | tail -1) \
    && echo "[ODBC Driver 18 for SQL Server]"        > /etc/odbcinst.ini \
    && echo "Description=Microsoft ODBC Driver 18"  >> /etc/odbcinst.ini \
    && echo "Driver=$DRIVER_PATH"                   >> /etc/odbcinst.ini \
    && echo "UsageCount=1"                          >> /etc/odbcinst.ini \
    && echo ""                                       >> /etc/odbcinst.ini \
    && echo "[ODBC]"                                >> /etc/odbcinst.ini \
    && echo "Trace=no"                              >> /etc/odbcinst.ini

# Créer odbc.ini avec DSN MSSQL (Encrypt=no forcé)
RUN echo "[MSSQL]"                                  > /etc/odbc.ini \
    && echo "Driver=ODBC Driver 18 for SQL Server" >> /etc/odbc.ini \
    && echo "Encrypt=no"                           >> /etc/odbc.ini \
    && echo "TrustServerCertificate=yes"           >> /etc/odbc.ini

# Vérifier que le driver SQL Server est bien installé et configuré
RUN odbcinst -q -d -n "ODBC Driver 18 for SQL Server" \
    && echo "Driver OK: $(find /opt/microsoft -name 'libmsodbcsql*.so*' 2>/dev/null | sort | tail -1)" \
    || echo "WARNING: Driver config check failed"

# Copier et installer les dépendances Python
COPY requirements/ requirements/
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements/docker.txt
RUN pip install --no-cache-dir waitress

# Copier le code source
COPY . .

# Créer les dossiers nécessaires
RUN mkdir -p /app/staticfiles \
             /app/media \
             /app/chroma_db \
             /app/django_cache \
             /app/logs

# Collecter les fichiers statiques
RUN python manage.py collectstatic --noinput --settings=config.settings

# Port exposé
EXPOSE 8000

# Script de démarrage
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
