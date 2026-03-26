from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from apps.ingestion.models import UploadedFile


@login_required
def home(request):
    recent_files = UploadedFile.objects.filter(
        uploaded_by=request.user
    ).order_by('-created_at')[:5]
    return render(request, 'dashboard/home.html', {
        'recent_files': recent_files
    })