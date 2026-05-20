from django.contrib import admin
from .models import ChatSession, ChatMessage


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display  = ('user', 'title', 'created_at')
    list_filter   = ('user',)
    search_fields = ('title', 'user__username')
    readonly_fields = ('created_at',)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display    = ('get_user', 'question', 'duration', 'duration_seconds', 'is_satisfied', 'created_at')
    list_filter     = ('session__user', 'is_satisfied')
    search_fields   = ('question', 'answer', 'session__user__username')
    readonly_fields = ('created_at', 'duration', 'duration_seconds')

    def get_user(self, obj):
        return obj.session.user
    get_user.short_description = 'Utilisateur'
