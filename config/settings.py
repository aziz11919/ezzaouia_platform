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
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

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
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ── Middleware ────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'apps.accounts.middleware.SessionTimeoutMiddleware',
    'apps.accounts.middleware.ForcePasswordChangeMiddleware',
    'apps.audit.middleware.AuditMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

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
# Prérequis : installer "ODBC Driver 17 for SQL Server"
# URL : https://aka.ms/downloadmsodbcsql
DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': config('DB_NAME', default='DBTEST'),
        'HOST': config('DB_SERVER', default=r'localhost\SQLEXPRESS'),
        'USER': config('DB_USER', default=''),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'OPTIONS': {
            'driver': 'ODBC Driver 17 for SQL Server',
            'extra_params': ';'.join([
                'Trusted_Connection=' + config('DB_TRUSTED_CONNECTION', default='no'),
                'Encrypt=' + config('DB_ENCRYPT', default='no'),
                'TrustServerCertificate=' + config('DB_TRUST_SERVER_CERTIFICATE', default='yes'),
            ]),
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
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Celery — Tâches asynchrones ───────────────────────────────────
# Broker : Memurai (Redis pour Windows) — port 6379
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://127.0.0.1:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
# Résultats stockés dans SQL Server via django-celery-results
CELERY_RESULT_BACKEND = 'django-db'

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
OLLAMA_MODEL    = config('OLLAMA_MODEL',    default='llama3')
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

# ── Email — MARETAP internal Outlook ─────────────────────────────
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = config('EMAIL_HOST',          default='smtp.maretap.tn')
EMAIL_PORT          = config('EMAIL_PORT',          default=587, cast=int)
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = config('EMAIL_HOST_USER',     default='noreply@maretap.tn')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL  = 'EZZAOUIA Platform <noreply@maretap.tn>'

# Platform base URL used in emails
PLATFORM_HOST = config('PLATFORM_HOST', default='192.168.87.x:8000')

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
