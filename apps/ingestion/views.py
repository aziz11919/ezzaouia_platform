import os
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import UploadedFile
from .tasks import process_uploaded_file
from django.conf import settings


@login_required
def upload_view(request):
    if request.method == 'POST' and request.FILES.get('file'):
        f = request.FILES['file']
        ext = os.path.splitext(f.name)[1].lower().replace('.', '')

        if ext not in ['pdf', 'docx', 'xlsx']:
            messages.error(request, "Format non supporté. Utilisez PDF, Word ou Excel.")
            return redirect('ingestion:upload')

        uploaded = UploadedFile.objects.create(
            file=f,
            original_name=f.name,
            file_type=ext,
            uploaded_by=request.user,
            status='pending',
        )

        # Lancer le traitement en arrière-plan (Celery)
        process_uploaded_file.delay(uploaded.id)
        messages.success(request, f"Fichier '{f.name}' uploadé — traitement en cours...")
        return redirect('ingestion:list')

    return render(request, 'ingestion/upload.html')


@login_required
def file_list_view(request):
    files = UploadedFile.objects.filter(
        uploaded_by=request.user
    ).order_by('-created_at')[:50]
    return render(request, 'ingestion/list.html', {'files': files})