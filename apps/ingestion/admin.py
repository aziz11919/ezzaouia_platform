from django.contrib import admin
from .models import UploadedFile

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display  = ('original_name', 'file_type', 'status',
                     'rows_extracted', 'uploaded_by', 'created_at')
    list_filter   = ('status', 'file_type')
    search_fields = ('original_name',)
    readonly_fields = ('created_at', 'updated_at', 'rows_extracted', 'error_msg')   