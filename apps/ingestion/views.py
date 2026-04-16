import os
import shutil
import logging
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib import messages
from .models import UploadedFile
from .tasks import process_uploaded_file
from django.conf import settings
from apps.audit.models import AuditLog
from apps.core.views import serve_react

logger = logging.getLogger('apps')


@login_required
def upload_view(request):
    if request.method == 'GET':
        return serve_react(request)

    if request.method == 'POST' and request.FILES.get('file'):
        f = request.FILES['file']
        ext = os.path.splitext(f.name)[1].lower().replace('.', '')

        if ext not in ['pdf', 'docx', 'xlsx']:
            messages.error(request, "Unsupported format. Use PDF, Word, or Excel.")
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
        messages.success(request, f"File '{f.name}' uploaded — processing in progress...")
        return redirect('ingestion:list')

    return serve_react(request)


@login_required
def file_list_view(request):
    return serve_react(request)


# ── API JSON pour React frontend ─────────────────────────────────

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST


@login_required
@require_GET
def api_recent_files(request):
    """GET /ingestion/recent/ — 10 derniers fichiers importés."""
    files = UploadedFile.objects.filter(
        uploaded_by=request.user
    ).order_by('-created_at')[:10]
    return JsonResponse({
        'files': [
            {
                'id':            f.id,
                'original_name': f.original_name,
                'file_type':     f.file_type,
                'status':        f.status,
                'created_at':    f.created_at.strftime('%d/%m/%Y %H:%M'),
            }
            for f in files
        ]
    })


@login_required
@require_POST
def api_upload(request):
    """POST /ingestion/api-upload/ — upload JSON/multipart pour React."""
    if not request.FILES.get('file'):
        return JsonResponse({'error': 'No file provided.'}, status=400)

    f   = request.FILES['file']
    ext = os.path.splitext(f.name)[1].lower().replace('.', '')

    if ext not in ['pdf', 'docx', 'xlsx']:
        return JsonResponse({'error': 'Unsupported format. Use PDF, Word, or Excel.'}, status=400)

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
        details={'filename': f.name, 'status': uploaded.status},
    )

    # Copie OneDrive optionnelle
    onedrive_dir = getattr(settings, 'ONEDRIVE_SYNC_DIR', None)
    if onedrive_dir:
        try:
            os.makedirs(onedrive_dir, exist_ok=True)
            dest = os.path.join(onedrive_dir, f.name)
            if os.path.exists(dest):
                base, extension = os.path.splitext(f.name)
                counter = 1
                while os.path.exists(dest):
                    dest = os.path.join(onedrive_dir, f"{base}_{counter}{extension}")
                    counter += 1
            shutil.copy2(uploaded.file.path, dest)
        except Exception as e:
            logger.error(f"Erreur copie OneDrive : {e}")

    from .tasks import process_uploaded_file
    process_uploaded_file.delay(uploaded.id)

    return JsonResponse({
        'success': True,
        'file': {
            'id':            uploaded.id,
            'original_name': uploaded.original_name,
            'file_type':     uploaded.file_type,
            'status':        uploaded.status,
            'created_at':    uploaded.created_at.strftime('%d/%m/%Y %H:%M'),
        },
    })


@login_required
@require_GET
def api_file_status(request, file_id):
    """GET /ingestion/api-status/<id>/ — statut d'un fichier."""
    try:
        f = UploadedFile.objects.get(id=file_id, uploaded_by=request.user)
    except UploadedFile.DoesNotExist:
        return JsonResponse({'error': 'Not found.'}, status=404)
    return JsonResponse({
        'id':     f.id,
        'status': f.status,
        'error':  getattr(f, 'error_message', '') or '',
    })
