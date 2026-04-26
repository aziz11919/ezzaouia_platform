from django.db import models
from apps.core.models import BaseModel


class UploadedFile(BaseModel):
    """User-uploaded file - PDF, Word, or Excel."""

    class FileType(models.TextChoices):
        PDF = 'pdf', 'PDF'
        DOCX = 'docx', 'Word'
        XLSX = 'xlsx', 'Excel'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        SUCCESS = 'success', 'Completed'
        ERROR = 'error', 'Error'

    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    original_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10, choices=FileType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    error_msg = models.TextField(blank=True)
    rows_extracted = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Uploaded file'
        verbose_name_plural = 'Uploaded files'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.original_name} ({self.get_status_display()})'
