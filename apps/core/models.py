"""
Modèle abstrait partagé par toutes les apps Django (sauf warehouse).
Les modèles warehouse utilisent managed=False (tables DWH existantes).
"""
from django.db import models


class BaseModel(models.Model):
    """Ajoute created_at / updated_at à tous les modèles métier."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
