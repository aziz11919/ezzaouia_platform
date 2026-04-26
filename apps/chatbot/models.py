from django.db import models
from apps.core.models import BaseModel


class ChatSession(BaseModel):
    """Conversation session - one user can have multiple sessions."""

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='sessions')
    title = models.CharField(max_length=200, default='New conversation')
    is_active = models.BooleanField(default=True)
    share_token = models.CharField(max_length=32, null=True, blank=True, unique=True)
    is_shared = models.BooleanField(default=False)
    shared_at = models.DateTimeField(null=True, blank=True)
    shared_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shared_sessions',
    )

    class Meta:
        verbose_name = 'Chat session'
        verbose_name_plural = 'Chat sessions'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} - {self.title}'

    def get_first_question(self):
        msg = self.messages.order_by('created_at').first()
        return msg.question[:60] if msg else 'New conversation'


class ChatMessage(BaseModel):
    """Message in a conversation session."""

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    question = models.TextField()
    answer = models.TextField()
    duration = models.FloatField(default=0)
    duration_seconds = models.FloatField(null=True, blank=True)
    is_satisfied = models.BooleanField(null=True, blank=True, default=None)

    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.session} - {self.question[:50]}'


class AnalysisComment(BaseModel):
    """Team comment on a chatbot answer."""

    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='chatbot_comments')
    content = models.TextField(max_length=500)
    is_public = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Analysis comment'
        verbose_name_plural = 'Analysis comments'
        ordering = ['created_at']

    def __str__(self):
        visibility = 'public' if self.is_public else 'private'
        return f'{self.author} - msg#{self.message_id} [{visibility}]'


class SessionShare(BaseModel):
    """Explicitly shared chat session with another user."""

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='shares')
    shared_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='sent_shares')
    shared_with = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='received_shares')
    viewed = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Session share'
        verbose_name_plural = 'Session shares'
        unique_together = ('session', 'shared_with')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.shared_by} -> {self.shared_with}: {self.session.title[:40]}'


class UserMemory(BaseModel):
    """Persistent memory per user from previous analyses."""

    TOPIC_CHOICES = [
        ('PRODUCTION', 'Production'),
        ('BUDGET', 'Budget / Costs'),
        ('WORKOVER', 'Workover / Interventions'),
        ('RESERVOIR', 'Reservoir'),
        ('GENERAL', 'General'),
    ]

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='memories')
    well_code = models.CharField(max_length=20, null=True, blank=True)
    topic = models.CharField(max_length=20, choices=TOPIC_CHOICES, default='GENERAL')
    summary = models.TextField(max_length=200)

    class Meta:
        verbose_name = 'User memory'
        verbose_name_plural = 'User memories'
        unique_together = ('user', 'well_code', 'topic')
        ordering = ['-updated_at']

    def __str__(self):
        label = self.well_code or 'Field overview'
        return f'{self.user} - {label} [{self.topic}]'
