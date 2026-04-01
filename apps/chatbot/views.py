import time
import json
import os
import logging
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import ChatSession, ChatMessage
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

    messages = session.messages.order_by('created_at') if session else []

    return render(request, 'chatbot/chat.html', {
        'sessions':        sessions,
        'current_session': session,
        'messages':        messages,
        'session_id_js':   session.id if session else 'null',
    })


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
        doc_id     = data.get('doc_id')
        filename   = data.get('filename')

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
        result = ask(question, history=history, doc_id=doc_id, filename=filename)
        duration = round(time.time() - start, 2)

        # If user clicked Stop while the LLM was running, discard the result
        if request.user.id in _stop_requests:
            _stop_requests.discard(request.user.id)
            return JsonResponse({'stopped': True})

        answer     = result['answer']
        chart_data = result.get('chart_data')
        suggestions = result.get('suggestions', [])

        ChatMessage.objects.create(
            session=session,
            question=question,
            answer=answer,
            duration=duration,
        )

        if session.title == 'Nouvelle conversation':
            session.title = question[:60]
            session.save()

        return JsonResponse({
            'answer':      answer,
            'duration':    duration,
            'session_id':  session.id,
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

    if ext not in ['pdf', 'docx']:
        return JsonResponse({
            'error': 'Seuls PDF et Word (.docx) sont acceptés.'
        }, status=400)

    try:
        from django.core.files.storage import default_storage
        path      = default_storage.save(f'chat_uploads/{f.name}', f)
        full_path = default_storage.path(path)

        if ext == 'pdf':
            from apps.ingestion.parsers import parse_pdf
            text, error = parse_pdf(full_path)
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