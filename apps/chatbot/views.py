import time
import json
import os
import logging
import secrets
from django.core.cache import cache
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.db import OperationalError, ProgrammingError
from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from apps.audit.models import AuditLog
from apps.core.views import serve_react
from apps.ingestion.models import UploadedFile
from .models import ChatSession, ChatMessage, AnalysisComment, SessionShare
from .morning_suggestions import generate_morning_suggestions
from .rag_pipeline import ask, index_document

logger = logging.getLogger('apps')

# In-memory set of user IDs that requested cancellation
_stop_requests: set = set()


def _cleanup_empty_sessions(user):
    """Supprimer les sessions sans aucun message."""
    try:
        ChatSession.objects.filter(user=user).annotate(
            msg_count=Count('messages')
        ).filter(msg_count=0).delete()
    except Exception:
        pass


def _sessions_list(user):
    return ChatSession.objects.filter(user=user).order_by('-created_at')[:20]


def _preselected_docs(request):
    docs = []
    doc_id = request.GET.get('doc_id', '').strip()
    if doc_id.isdigit():
        selected = (
            UploadedFile.objects.filter(id=int(doc_id), status='success')
            .values('id', 'original_name', 'file_type')
            .first()
        )
        if selected:
            docs.append({
                'id':        selected['id'],
                'name':      selected['original_name'],
                'file_type': selected['file_type'],
            })
    return docs


@login_required
def chat_view(request):
    return serve_react(request)


@login_required
def session_view(request, session_id):
    return serve_react(request)


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
    """Clean empty sessions and redirect to chat, preserving doc_id if present."""
    _cleanup_empty_sessions(request.user)
    doc_id = request.GET.get('doc_id', '').strip()
    if doc_id.isdigit():
        return redirect(f'/chatbot/?doc_id={doc_id}')
    return redirect('chatbot:chat')


@login_required
@require_GET
def api_doc_info(request):
    """GET /chatbot/doc-info/?doc_id=X — returns doc info for React pre-selection."""
    docs = _preselected_docs(request)
    return JsonResponse({'docs': docs})


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
            return JsonResponse({'error': 'Question is empty.'}, status=400)
        if len(question) > 1000:
            return JsonResponse({'error': 'Question is too long.'}, status=400)

        session = None
        if session_id and str(session_id) not in ('null', 'None', ''):
            try:
                session = ChatSession.objects.get(
                    id=int(session_id), user=request.user
                )
            except (ChatSession.DoesNotExist, ValueError, TypeError):
                session = None

        if not session:
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
                    'error': "Chatbot database is not migrated. Run 'python manage.py migrate chatbot'."
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

        # ── Option D : commentaires publics sur des questions similaires ──
        related_comments = []
        try:
            from django.db.models import Count, Q as DQ
            words = [w for w in question.split() if len(w) >= 4][:6]
            if words:
                q_filter = DQ()
                for w in words:
                    q_filter |= DQ(question__icontains=w)
                candidates = (
                    ChatMessage.objects
                    .filter(q_filter)
                    .exclude(session=session)
                    .annotate(pub_count=Count(
                        'comments',
                        filter=DQ(comments__is_public=True),
                    ))
                    .filter(pub_count__gt=0)
                    .prefetch_related('comments__author')
                    .order_by('-created_at')[:5]
                )
                for m in candidates:
                    pub = [c for c in m.comments.all() if c.is_public][:2]
                    if pub:
                        related_comments.append({
                            'question': m.question[:120],
                            'comments': [
                                {
                                    'author':  c.author.get_full_name() or c.author.username,
                                    'content': c.content[:200],
                                }
                                for c in pub
                            ],
                        })
                    if len(related_comments) >= 2:
                        break
        except Exception as exc:
            logger.debug(f"related_comments lookup skipped: {exc}")

        return JsonResponse({
            'answer':           answer,
            'duration':         duration,
            'session_id':       session.id,
            'message_id':       chat_message.id,
            'chart_data':       chart_data,
            'suggestions':      suggestions,
            'related_comments': related_comments,
        })

    except Exception as e:
        logger.error(f"ask_view error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def upload_chat_file(request):
    if not request.FILES.get('file'):
        return JsonResponse({'error': 'No file provided.'}, status=400)

    f   = request.FILES['file']
    ext = os.path.splitext(f.name)[1].lower().replace('.', '')

    if ext not in ['pdf', 'docx', 'xlsx']:
        return JsonResponse({
            'error': 'Only PDF, Word (.docx), and Excel (.xlsx) files are supported.'
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
            'message':  f"'{f.name}' indexed ({chunks} chunks).",
            'filename': f.name,
            'doc_id':   doc_id,
            'chunks':   chunks,
        })

    except Exception as e:
        logger.error(f"chat upload error: {e}")
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
        logger.error(f"delete_session error: {e}")
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
            return JsonResponse({'error': 'Title is empty.'}, status=400)
        if len(title) > 200:
            return JsonResponse({'error': 'Title is too long.'}, status=400)
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        session.title = title
        session.save(update_fields=['title'])
        return JsonResponse({'success': True, 'title': title})
    except Exception as e:
        logger.error(f"rename_session error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def add_comment(request):
    """Ajouter un commentaire sur une réponse chatbot."""
    try:
        data = json.loads(request.body)
        message_id = data.get('message_id')
        content    = (data.get('content') or '').strip()
        is_public  = bool(data.get('is_public', True))

        try:
            message_id = int(message_id)
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Invalid message_id.'}, status=400)

        if not content:
            return JsonResponse({'error': 'Content is empty.'}, status=400)
        if len(content) > 500:
            return JsonResponse({'error': 'Content is too long (max 500 characters).'}, status=400)

        message = get_object_or_404(ChatMessage, id=message_id)

        comment = AnalysisComment.objects.create(
            message=message,
            author=request.user,
            content=content,
            is_public=is_public,
        )

        return JsonResponse({
            'success':    True,
            'comment_id': comment.id,
            'author':     request.user.get_full_name() or request.user.username,
            'created_at': comment.created_at.strftime('%d/%m/%Y %H:%M'),
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)
    except Exception as e:
        logger.error(f"add_comment error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def get_comments(request, message_id):
    """Retourner les commentaires d'un message (publics + privés propres à l'user)."""
    try:
        message = get_object_or_404(ChatMessage, id=message_id)

        qs = AnalysisComment.objects.filter(message=message).select_related('author')
        comments = []
        for c in qs:
            if c.is_public or c.author_id == request.user.id:
                comments.append({
                    'id':         c.id,
                    'author':     c.author.get_full_name() or c.author.username,
                    'content':    c.content,
                    'is_public':  c.is_public,
                    'created_at': c.created_at.strftime('%d/%m/%Y %H:%M'),
                    'is_mine':    c.author_id == request.user.id,
                })

        return JsonResponse({'comments': comments, 'total': len(comments)})

    except Exception as e:
        logger.error(f"get_comments error: {e}")
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
            return JsonResponse({'error': 'Invalid message_id.'}, status=400)

        if isinstance(rating_raw, bool):
            rating = rating_raw
        elif isinstance(rating_raw, str):
            value = rating_raw.strip().lower()
            if value in {'true', '1', 'up', 'like'}:
                rating = True
            elif value in {'false', '0', 'down', 'dislike'}:
                rating = False
            else:
                return JsonResponse({'error': 'Invalid rating.'}, status=400)
        else:
            return JsonResponse({'error': 'Invalid rating.'}, status=400)

        qs = ChatMessage.objects.select_related('session').filter(id=message_id)
        if not getattr(request.user, 'is_admin', False):
            qs = qs.filter(session__user=request.user)

        msg = qs.first()
        if msg is None:
            return JsonResponse({'error': 'Message not found.'}, status=404)

        msg.is_satisfied = rating
        msg.save(update_fields=['is_satisfied'])
        return JsonResponse({'success': True, 'message_id': msg.id, 'is_satisfied': msg.is_satisfied})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)
    except Exception as e:
        logger.error(f"rate_view error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def list_users(request):
    """Liste des utilisateurs disponibles pour le partage."""
    from apps.accounts.models import User
    users = (
        User.objects
        .exclude(id=request.user.id)
        .filter(is_active=True)
        .values('id', 'username', 'first_name', 'last_name', 'role')
        .order_by('first_name', 'last_name')
    )
    result = []
    for u in users:
        full_name = f"{u['first_name']} {u['last_name']}".strip() or u['username']
        result.append({
            'id':        u['id'],
            'username':  u['username'],
            'full_name': full_name,
            'role':      u.get('role', ''),
        })
    return JsonResponse({'users': result})


@login_required
@require_GET
def shared_with_me(request):
    """Sessions partagées avec l'utilisateur courant."""
    shares = (
        SessionShare.objects
        .filter(shared_with=request.user)
        .select_related('session', 'shared_by')
        .order_by('-created_at')[:15]
    )
    result = [
        {
            'session_id': s.session_id,
            'title':      s.session.title,
            'shared_by':  s.shared_by.get_full_name() or s.shared_by.username,
            'token':      s.session.share_token,
            'viewed':     s.viewed,
            'shared_at':  s.created_at.strftime('%d/%m/%Y'),
        }
        for s in shares
        if s.session.share_token and s.session.is_shared
    ]
    return JsonResponse({'shared_sessions': result})


@login_required
@require_POST
def share_session(request, session_id):
    """Partager une session avec des utilisateurs sélectionnés."""
    try:
        data     = json.loads(request.body) if request.body else {}
        user_ids = data.get('user_ids', [])

        session = get_object_or_404(ChatSession, id=session_id, user=request.user)

        if not session.share_token:
            session.share_token = secrets.token_hex(16)
        session.is_shared = True
        session.shared_at = timezone.now()
        session.shared_by = request.user
        session.save(update_fields=['share_token', 'is_shared', 'shared_at', 'shared_by'])

        from apps.accounts.models import User
        shared_count = 0
        for uid in user_ids:
            try:
                target = User.objects.get(id=int(uid), is_active=True)
                SessionShare.objects.get_or_create(
                    session=session,
                    shared_with=target,
                    defaults={'shared_by': request.user},
                )
                shared_count += 1
            except (User.DoesNotExist, ValueError):
                pass

        return JsonResponse({
            'share_url':    f'/chatbot/shared/{session.share_token}/',
            'shared_count': shared_count,
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)
    except Exception as e:
        logger.error(f"share_session error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def shared_session_view(request, token):
    """Afficher une session partagée en lecture seule."""
    session = get_object_or_404(
        ChatSession.objects.select_related('user'),
        share_token=token,
        is_shared=True,
    )

    is_owner = session.user_id == request.user.id
    is_shared_with_user = SessionShare.objects.filter(
        session=session,
        shared_with=request.user,
    ).exists()

    if not (is_owner or is_shared_with_user or getattr(request.user, 'is_admin', False)):
        django_messages.error(request, "Unauthorized access.")
        return redirect('chatbot:chat')

    if is_shared_with_user:
        SessionShare.objects.filter(session=session, shared_with=request.user).update(viewed=True)

    context = {
        'session': session,
        'messages': session.messages.order_by('created_at'),
    }
    return render(request, 'chatbot/shared_session.html', context)


# ── API JSON pour React frontend ─────────────────────────────────

@login_required
@require_GET
def api_sessions(request):
    """GET /chatbot/sessions/ — liste des sessions de l'utilisateur."""
    _cleanup_empty_sessions(request.user)
    sessions = ChatSession.objects.filter(user=request.user).order_by('-created_at')[:30]
    return JsonResponse({
        'sessions': [
            {
                'id':         s.id,
                'title':      s.title,
                'created_at': s.created_at.strftime('%d/%m/%Y %H:%M'),
            }
            for s in sessions
        ]
    })


@login_required
@require_GET
def api_session_messages(request, session_id):
    """GET /chatbot/session/<id>/messages/ — messages d'une session."""
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    msgs = session.messages.order_by('created_at')
    return JsonResponse({
        'session_id': session.id,
        'title':      session.title,
        'messages': [
            {
                'id':         m.id,
                'question':   m.question,
                'answer':     m.answer,
                'duration':   getattr(m, 'duration_seconds', None),
                'created_at': m.created_at.strftime('%d/%m/%Y %H:%M'),
            }
            for m in msgs
        ]
    })

