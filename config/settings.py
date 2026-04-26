"""
Settings Django — Plateforme EZZAOUIA / MARETAP
100% On-Premise : SQL Server local + Celery/Redis local + Ollama local
"""
from pathlib import Path
from decouple import config

# ── Chemins ───────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Sécurité ──────────────────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY', default='dev-insecure-key-changez-moi')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,0.0.0.0').split(',')

# ── Applications ──────────────────────────────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
THIRD_PARTY_APPS = [
    'rest_framework',
    'guardian',
    'django_celery_results',
    'django_celery_beat',
    'corsheaders',
]
LOCAL_APPS = [
    'apps.core',
    'apps.accounts',
    'apps.warehouse',
    'apps.ingestion',
    'apps.bibliotheque',
    'apps.reports',
    'apps.kpis',
    'apps.chatbot',
    'apps.dashboard',
    'apps.audit',
    'apps.forecasting',
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ── Middleware ────────────────────────────────────────────────────
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'apps.accounts.middleware.SessionTimeoutMiddleware',
    'apps.accounts.middleware.ForcePasswordChangeMiddleware',
    'apps.audit.middleware.AuditMiddleware',
    'apps.core.middleware.ContentSecurityPolicyMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Required for React template mirroring inside same-origin iframes.
X_FRAME_OPTIONS = 'SAMEORIGIN'

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ── Base de données — SQL Server On-Premise ───────────────────────
# Prérequis : installer "ODBC Driver 18 for SQL Server"
# URL : https://aka.ms/downloadmsodbcsql
# Driver 18 active Encrypt=yes par défaut — désactivé ici (réseau interne MARETAP)
_db_server   = config('DB_SERVER',   default=r'localhost\SQLEXPRESS')
_db_name     = config('DB_NAME',     default='DBTEST')
_db_user     = config('DB_USER',     default='')
_db_password = config('DB_PASSWORD', default='')

DATABASES = {
    'default': {
        'ENGINE':   'mssql',
        'NAME':     _db_name,
        'HOST':     _db_server,
        'USER':     _db_user,
        'PASSWORD': _db_password,
        'PORT':     '',
        'OPTIONS': {
            'driver': 'ODBC Driver 18 for SQL Server',
            'extra_params': (
                'Encrypt=no;'
                'TrustServerCertificate=yes;'
                'Connection Timeout=30;'
            ),
        },
    }
}

# ── Auth personnalisé ─────────────────────────────────────────────
AUTH_USER_MODEL = 'accounts.User'
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
]
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Session timeout: 30 minutes d'inactivite
SESSION_COOKIE_AGE = 1800
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalisation ──────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Tunis'
USE_I18N = True
USE_TZ = True

# ── Fichiers statiques & media ────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
}
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Celery — Tâches asynchrones ───────────────────────────────────
# Broker : Memurai (Redis pour Windows) — port 6379
CELERY_BROKER_URL = config('CELERY_BROKER_URL',default='redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
# Résultats : 'django-db' (SQL Server) ou 'redis://redis:6379/0' (Docker Redis)
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='django-db')

# ── Django REST Framework ─────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
}

# ── Configuration IA / RAG ────────────────────────────────────────
OLLAMA_BASE_URL = config('OLLAMA_BASE_URL', default='http://127.0.0.1:11434')
OLLAMA_MODEL    = config('OLLAMA_MODEL',    default='llama3.1:8b')
OLLAMA_NUM_CTX = config('OLLAMA_NUM_CTX', default=4096, cast=int)
OLLAMA_NUM_PREDICT = config('OLLAMA_NUM_PREDICT', default=900, cast=int)
OLLAMA_TIMEOUT = config('OLLAMA_TIMEOUT', default=180, cast=int)
CHROMA_PERSIST_DIR = config('CHROMA_PERSIST_DIR', default=str(BASE_DIR / 'chroma_db'))

# ── Upload fichiers ───────────────────────────────────────────────
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS   = ['.pdf', '.docx', '.xlsx', '.xls']
# Dossier OneDrive partagé MARETAP — copie automatique de chaque upload
ONEDRIVE_SYNC_DIR = config(
    'ONEDRIVE_SYNC_DIR',
    default=r'C:\Users\Mega-PC\OneDrive - MARETAP SA\Attachments\aaaaa',
)

# ── Email — Office 365 / MARETAP Outlook ─────────────────────────
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp.office365.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True   # STARTTLS on port 587
EMAIL_USE_SSL       = False  # mutual exclusion with TLS — never use port 465
EMAIL_HOST_USER     = 'aziz.stage@maretap.tn'
EMAIL_HOST_PASSWORD = config('EMAIL_PASSWORD', default='')  # set EMAIL_PASSWORD in .env
DEFAULT_FROM_EMAIL  = 'EZZAOUIA Platform <aziz.stage@maretap.tn>'
EMAIL_TIMEOUT       = 30

# Platform base URL used in emails
PLATFORM_HOST = config('PLATFORM_HOST', default='192.168.87.x:8000')

# ── CORS — React frontend (http://localhost:3000) ─────────────────
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
CORS_ALLOW_CREDENTIALS = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]

# ── Logging ───────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {module} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'apps': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
    },
}
