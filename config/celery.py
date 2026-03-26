"""
Configuration Celery — Plateforme EZZAOUIA
Tâches async : extraction fichiers, calcul KPIs, indexation RAG
"""
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('ezzaouia_platform')

# Lire la config Celery depuis settings.py (préfixe CELERY_)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-découverte des tasks.py dans chaque app
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
