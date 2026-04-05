from django.db import models
from apps.core.models import BaseModel


class ChatSession(BaseModel):
    """Session de conversation — un utilisateur peut avoir plusieurs sessions."""
    user  = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='sessions')
    title = models.CharField(max_length=200, default='Nouvelle conversation')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name        = 'Session chat'
        verbose_name_plural = 'Sessions chat'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} — {self.title}'

    def get_first_question(self):
        msg = self.messages.order_by('created_at').first()
        return msg.question[:60] if msg else 'Nouvelle conversation'


class ChatMessage(BaseModel):
    """Message dans une session de conversation."""
    session  = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    question = models.TextField()
    answer   = models.TextField()
    duration = models.FloatField(default=0)
    duration_seconds = models.FloatField(null=True, blank=True)
    is_satisfied = models.BooleanField(null=True, blank=True, default=None)

    class Meta:
        verbose_name        = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.session} — {self.question[:50]}'


class UserMemory(BaseModel):
    """Mémoire persistante par utilisateur — retient les analyses des sessions précédentes."""
    TOPIC_CHOICES = [
        ('PRODUCTION', 'Production'),
        ('BUDGET',     'Budget / Coûts'),
        ('WORKOVER',   'Workover / Interventions'),
        ('RESERVOIR',  'Réservoir'),
        ('GENERAL',    'Général'),
    ]

    user      = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='memories')
    well_code = models.CharField(max_length=20, null=True, blank=True)
    topic     = models.CharField(max_length=20, choices=TOPIC_CHOICES, default='GENERAL')
    summary   = models.TextField(max_length=200)

    class Meta:
        verbose_name        = 'Mémoire utilisateur'
        verbose_name_plural = 'Mémoires utilisateur'
        unique_together     = ('user', 'well_code', 'topic')
        ordering            = ['-updated_at']

    def __str__(self):
        label = self.well_code or 'Champ global'
        return f'{self.user} — {label} [{self.topic}]'
