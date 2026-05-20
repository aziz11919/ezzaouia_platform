"""
Modele abstrait partage par toutes les apps Django (sauf warehouse).
Les modeles warehouse utilisent managed=False (tables DWH existantes).
"""
from django.db import models


class BaseModel(models.Model):
    """Ajoute created_at / updated_at a tous les modeles metier."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SiteConfiguration(models.Model):
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(
        default="The platform is currently under maintenance. Please try again in a few moments."
    )
    maintenance_start = models.DateTimeField(null=True, blank=True)
    estimated_end = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Configuration du site"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
