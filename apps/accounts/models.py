from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN     = 'admin',     'Administrator'
        INGENIEUR = 'ingenieur', 'Engineer'
        DIRECTION = 'direction', 'Management'

    role       = models.CharField(max_length=20, choices=Role.choices, default=Role.INGENIEUR)
    department = models.CharField(max_length=100, blank=True)
    phone      = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name        = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f'{self.get_full_name()} ({self.get_role_display()})'

    @property
    def is_admin(self):     return self.role == self.Role.ADMIN
    @property
    def is_ingenieur(self): return self.role == self.Role.INGENIEUR
    @property
    def is_direction(self): return self.role == self.Role.DIRECTION
