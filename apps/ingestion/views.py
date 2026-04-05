import os
import shutil
import logging
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import UploadedFile
from .tasks import process_uploaded_file
from django.conf import settings
from apps.audit.models import AuditLog

logger = logging.getLogger('apps')


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

        AuditLog.log(
            action=AuditLog.Action.UPLOAD_FILE,
            user=request.user,
            request=request,
            details={
                'filename': f.name,
                'status': uploaded.status,
            },
        )

        # Copie automatique vers le dossier OneDrive partagé MARETAP
        onedrive_dir = getattr(settings, 'ONEDRIVE_SYNC_DIR', None)
        if onedrive_dir:
            try:
                os.makedirs(onedrive_dir, exist_ok=True)
                dest = os.path.join(onedrive_dir, f.name)
                # Éviter l'écrasement silencieux : ajouter un suffixe si le fichier existe déjà
                if os.path.exists(dest):
                    base, ext = os.path.splitext(f.name)
                    counter = 1
                    while os.path.exists(dest):
                        dest = os.path.join(onedrive_dir, f"{base}_{counter}{ext}")
                        counter += 1
                shutil.copy2(uploaded.file.path, dest)
                logger.info(f"Copie OneDrive OK : {dest}")
            except Exception as e:
                logger.error(f"Erreur copie OneDrive : {e}")

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
