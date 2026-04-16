from datetime import datetime

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import OperationalError, ProgrammingError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from .models import AuditLog
from apps.core.views import serve_react


def _parse_iso_date(raw_value):
    if not raw_value:
        return None
    try:
        return datetime.strptime(raw_value, "%Y-%m-%d").date()
    except ValueError:
        return None


@login_required
def audit_log_list(request):
    # Frontend is now rendered by React SPA.
    return serve_react(request)

    if getattr(request.user, "role", None) not in {"admin", "direction"}:
        messages.error(request, "Unauthorized access.")
        return redirect("dashboard:home")

    user_filter = request.GET.get("user", "").strip()
    action_filter = request.GET.get("action", "").strip()
    start_date_raw = request.GET.get("start_date", "").strip()
    end_date_raw = request.GET.get("end_date", "").strip()

    try:
        logs = AuditLog.objects.select_related("user").all()

        if user_filter.isdigit():
            logs = logs.filter(user_id=int(user_filter))

        allowed_actions = {action for action, _ in AuditLog.Action.choices}
        if action_filter in allowed_actions:
            logs = logs.filter(action=action_filter)

        start_date = _parse_iso_date(start_date_raw)
        if start_date_raw and start_date:
            logs = logs.filter(created_at__date__gte=start_date)
        elif start_date_raw:
            messages.warning(request, "Invalid start date.")

        end_date = _parse_iso_date(end_date_raw)
        if end_date_raw and end_date:
            logs = logs.filter(created_at__date__lte=end_date)
        elif end_date_raw:
            messages.warning(request, "Invalid end date.")

        paginator = Paginator(logs, 20)
        page_obj = paginator.get_page(request.GET.get("page"))

        users_with_logs = get_user_model().objects.filter(
            id__in=AuditLog.objects.exclude(user__isnull=True)
            .values_list("user_id", flat=True)
            .distinct()
        ).order_by("username")
    except (ProgrammingError, OperationalError):
        messages.error(
            request,
            "Audit table is missing. Run 'python manage.py migrate audit' and reload the page.",
        )
        users_with_logs = get_user_model().objects.none()
        page_obj = Paginator([], 20).get_page(1)

    query_params = request.GET.copy()
    query_params.pop("page", None)

    context = {
        "page_obj": page_obj,
        "users": users_with_logs,
        "actions": AuditLog.Action.choices,
        "user_filter": user_filter,
        "action_filter": action_filter,
        "start_date": start_date_raw,
        "end_date": end_date_raw,
        "query_string": query_params.urlencode(),
    }
    return render(request, "audit/log.html", context)


@login_required
@require_GET
def api_logs(request):
    """GET /api/audit/logs/ - JSON log list for React."""
    if getattr(request.user, "role", None) not in {"admin", "direction"}:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    user_filter = request.GET.get("user", "").strip()
    action_filter = request.GET.get("action", "").strip()
    start_date_raw = request.GET.get("start_date", "").strip()
    end_date_raw = request.GET.get("end_date", "").strip()

    logs = AuditLog.objects.select_related("user").all()
    if user_filter.isdigit():
        logs = logs.filter(user_id=int(user_filter))

    allowed_actions = {action for action, _ in AuditLog.Action.choices}
    if action_filter in allowed_actions:
        logs = logs.filter(action=action_filter)

    start_date = _parse_iso_date(start_date_raw)
    if start_date_raw and start_date:
        logs = logs.filter(created_at__date__gte=start_date)

    end_date = _parse_iso_date(end_date_raw)
    if end_date_raw and end_date:
        logs = logs.filter(created_at__date__lte=end_date)

    paginator = Paginator(logs, 20)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    users_with_logs = get_user_model().objects.filter(
        id__in=AuditLog.objects.exclude(user__isnull=True)
        .values_list("user_id", flat=True)
        .distinct()
    ).order_by("username")

    results = []
    for log in page_obj.object_list:
        results.append({
            "id": log.id,
            "created_at": log.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            "user_name": (log.user.get_full_name() or log.user.username) if log.user else "",
            "action": log.action,
            "details_display": log.details_display,
            "ip_address": log.ip_address or "",
            "duration_display": log.duration_display,
        })

    return JsonResponse({
        "results": results,
        "users": [
            {"id": u.id, "name": u.get_full_name() or u.username}
            for u in users_with_logs
        ],
        "actions": [a for a, _ in AuditLog.Action.choices],
        "page": page_obj.number,
        "pages": paginator.num_pages,
        "total": paginator.count,
    })
