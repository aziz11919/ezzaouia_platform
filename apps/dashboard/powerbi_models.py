from django.db import models


class PowerBIReport(models.Model):
    ROLE_ALL        = 'all'
    ROLE_ADMIN      = 'admin'
    ROLE_INGENIEUR  = 'ingenieur'
    ROLE_DIRECTION  = 'direction'
    ROLE_CHOICES = [
        (ROLE_ALL,       'All roles'),
        (ROLE_ADMIN,     'Admin only'),
        (ROLE_INGENIEUR, 'Ingénieur'),
        (ROLE_DIRECTION, 'Direction'),
    ]

    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    embed_url   = models.URLField(max_length=2000)
    icon        = models.CharField(max_length=10, default='📊')
    role        = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_ALL)
    order       = models.PositiveIntegerField(default=0)
    active      = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'dashboard'
        ordering  = ['order', 'title']

    def __str__(self):
        return self.title
