import time
import json
import os
import logging
from django.core.cache import cache
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.db import OperationalError, ProgrammingError
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from apps.audit.models import AuditLog
from apps.ingestion.models import UploadedFile
from .models import ChatSession, ChatMessage
from .morning_suggestions import generate_morning_suggestions
from .rag_pipeline import ask, index_document

logger = logging.getLogger('apps')

# In-memory set of user IDs that requested cancellation
_stop_requests: set = set()


@login_required
def chatbot_view(request, session_id=None):
    sessions = ChatSession.objects.filter(
        user=request.user
    ).order_by('-created_at')[:20]

    if session_id:
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    else:
        session = None  # always show fresh welcome screen when no session_id

    chat_messages = []
    if session:
        try:
            chat_messages = list(session.messages.order_by('created_at'))
        except (ProgrammingError, OperationalError):
            django_messages.error(
                request,
                "Base non migree pour le chatbot. Executez: python manage.py migrate chatbot",
            )
            chat_messages = []

    preselected_docs = []
    doc_id = request.GET.get('doc_id', '').strip()
    if doc_id.isdigit():
        selected = (
            UploadedFile.objects.filter(id=int(doc_id), status='success')
            .values('id', 'original_name', 'file_type')
            .first()
        )
        if selected:
            preselected_docs.append({
                'id': selected['id'],
                'name': selected['original_name'],
                'file_type': selected['file_type'],
            })

    return render(request, 'chatbot/chat.html', {
        'sessions':        sessions,
        'current_session': session,
        'messages':        chat_messages,
        'session_id_js':   session.id if session else 'null',
        'preselected_docs_json': json.dumps(preselected_docs),
    })


@login_required
@require_GET
def morning_suggestions_view(request):
    now = timezone.localtime()
    hour = now.hour
    cache_key = f"chatbot:morning_suggestions:{now.date().isoformat()}"

    if 6 <= hour < 17:
        suggestions = cache.get(cache_key)
        if suggestions is None:
            suggestions = generate_morning_suggestions()
            cache.set(cache_key, suggestions, 60 * 60 * 4)
        period = "morning" if hour < 13 else "afternoon"
        return JsonResponse({"suggestions": suggestions, "period": period})

    return JsonResponse({"suggestions": [], "period": "off_hours"})


@login_required
def new_session(request):
    session = ChatSession.objects.create(
        user=request.user,
        title='Nouvelle conversation',
    )
    return redirect('chatbot:session', session_id=session.id)


@login_required
@require_POST
def ask_view(request):
    try:
        data       = json.loads(request.body)
        question   = data.get('question', '').strip()
        session_id = data.get('session_id')
        filename   = data.get('filename')

        # Support multi-fichiers : doc_ids (liste) ou doc_id singulier (compat)
        doc_ids = data.get('doc_ids', [])
        if not doc_ids and data.get('doc_id'):
            doc_ids = [data['doc_id']]

        if not question:
            return JsonResponse({'error': 'Question vide.'}, status=400)
        if len(question) > 1000:
            return JsonResponse({'error': 'Question trop longue.'}, status=400)

        if session_id:
            session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        else:
            session = ChatSession.objects.create(
                user=request.user,
                title=question[:60],
            )

        history = [
            {'question': m.question, 'answer': m.answer}
            for m in session.messages.order_by('created_at')
        ]

        # Clear any stale stop flag before starting
        _stop_requests.discard(request.user.id)

        start  = time.time()
        result = ask(question, history=history, doc_ids=doc_ids, filename=filename, user=request.user)
        duration = round(time.time() - start, 2)

        # If user clicked Stop while the LLM was running, discard the result
        if request.user.id in _stop_requests:
            _stop_requests.discard(request.user.id)
            return JsonResponse({'stopped': True})

        answer     = result['answer']
        chart_data = result.get('chart_data')
        suggestions = result.get('suggestions', [])

        try:
            chat_message = ChatMessage.objects.create(
                session=session,
                question=question,
                answer=answer,
                duration=duration,
                duration_seconds=duration,
            )
        except (ProgrammingError, OperationalError):
            return JsonResponse(
                {
                    'error': "Base non migree pour le chatbot. Lancez 'python manage.py migrate chatbot'."
                },
                status=500,
            )

        AuditLog.log(
            action=AuditLog.Action.CHATBOT_QUESTION,
            user=request.user,
            request=request,
            details={
                'question': question[:200],
                'duration': duration,
                'session_id': session.id,
            },
        )

        if session.title == 'Nouvelle conversation':
            session.title = question[:60]
            session.save()

        return JsonResponse({
            'answer':      answer,
            'duration':    duration,
            'session_id':  session.id,
            'message_id':  chat_message.id,
            'chart_data':  chart_data,
            'suggestions': suggestions,
        })

    except Exception as e:
        logger.error(f"Erreur ask_view : {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def upload_chat_file(request):
    if not request.FILES.get('file'):
        return JsonResponse({'error': 'Aucun fichier.'}, status=400)

    f   = request.FILES['file']
    ext = os.path.splitext(f.name)[1].lower().replace('.', '')

    if ext not in ['pdf', 'docx', 'xlsx']:
        return JsonResponse({
            'error': 'Seuls PDF, Word (.docx) et Excel (.xlsx) sont acceptés.'
        }, status=400)

    try:
        from django.core.files.storage import default_storage
        path      = default_storage.save(f'chat_uploads/{f.name}', f)
        full_path = default_storage.path(path)

        if ext == 'pdf':
            from apps.ingestion.parsers import parse_pdf
            text, error = parse_pdf(full_path)
        elif ext == 'xlsx':
            from apps.ingestion.parsers import parse_excel
            text, error = parse_excel(full_path)
        else:
            from apps.ingestion.parsers import parse_word
            text, error = parse_word(full_path)

        if error:
            return JsonResponse({'error': error}, status=500)

        import hashlib
        doc_id = hashlib.md5(f.name.encode()).hexdigest()[:8]

        chunks = index_document(
            text,
            metadata={
                'filename':    f.name,
                'file_type':   ext,
                'uploaded_by': str(request.user),
                'doc_id':      doc_id,
            },
            doc_id=doc_id,
        )

        return JsonResponse({
            'message':  f"'{f.name}' indexé ({chunks} segments).",
            'filename': f.name,
            'doc_id':   doc_id,
            'chunks':   chunks,
        })

    except Exception as e:
        logger.error(f"Erreur upload chat : {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def delete_session(request, session_id):
    """Supprimer une session de conversation."""
    try:
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        session.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Erreur delete_session : {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def stop_generation(request):
    """Signal that the current LLM generation should be discarded."""
    _stop_requests.add(request.user.id)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def rename_session(request, session_id):
    """Renommer une session de conversation."""
    try:
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        if not title:
            return JsonResponse({'error': 'Titre vide.'}, status=400)
        if len(title) > 200:
            return JsonResponse({'error': 'Titre trop long.'}, status=400)
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        session.title = title
        session.save(update_fields=['title'])
        return JsonResponse({'success': True, 'title': title})
    except Exception as e:
        logger.error(f"Erreur rename_session : {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def rate_view(request):
    """Enregistrer l'evaluation utilisateur d'une reponse chatbot."""
    try:
        data = json.loads(request.body)
        message_id = data.get('message_id')
        rating_raw = data.get('rating')

        try:
            message_id = int(message_id)
        except (TypeError, ValueError):
            return JsonResponse({'error': 'message_id invalide.'}, status=400)

        if isinstance(rating_raw, bool):
            rating = rating_raw
        elif isinstance(rating_raw, str):
            value = rating_raw.strip().lower()
            if value in {'true', '1', 'up', 'like'}:
                rating = True
            elif value in {'false', '0', 'down', 'dislike'}:
                rating = False
            else:
                return JsonResponse({'error': 'rating invalide.'}, status=400)
        else:
            return JsonResponse({'error': 'rating invalide.'}, status=400)

        qs = ChatMessage.objects.select_related('session').filter(id=message_id)
        if not getattr(request.user, 'is_admin', False):
            qs = qs.filter(session__user=request.user)

        msg = qs.first()
        if msg is None:
            return JsonResponse({'error': 'Message introuvable.'}, status=404)

        msg.is_satisfied = rating
        msg.save(update_fields=['is_satisfied'])
        return JsonResponse({'success': True, 'message_id': msg.id, 'is_satisfied': msg.is_satisfied})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalide.'}, status=400)
    except Exception as e:
        logger.error(f"Erreur rate_view : {e}")
        return JsonResponse({'error': str(e)}, status=500)
