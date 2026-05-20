from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "ip_address", "duration_col", "short_details")
    list_filter = ("action", "created_at", "user")
    search_fields = ("user__username", "details", "ip_address", "user_agent")
    readonly_fields = ("user", "action", "details", "ip_address", "user_agent", "created_at")
    ordering = ("-created_at",)

    def short_details(self, obj):
        details = obj.details_display
        if len(details) <= 120:
            return details
        return f"{details[:117]}..."

    short_details.short_description = "Details"

    def duration_col(self, obj):
        return obj.duration_display

    duration_col.short_description = "Duration"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        return False
