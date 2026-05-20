from django.contrib import admin
from .powerbi_models import PowerBIReport


@admin.register(PowerBIReport)
class PowerBIReportAdmin(admin.ModelAdmin):
    list_display  = ['title', 'role', 'active', 'order', 'created_at']
    list_editable = ['active', 'order']
    list_filter   = ['role', 'active']
    search_fields = ['title', 'description']
    ordering      = ['order', 'title']
