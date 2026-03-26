# Chargement automatique de Celery au démarrage Django
from .celery import app as celery_app
__all__ = ('celery_app',)
