import json

from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_GET, require_POST

from apps.core.models import SiteConfiguration


def _is_admin(user):
    return bool(
        user
        and user.is_authenticated
        and getattr(user, "role", "") == "admin"
    )


def _serialize_config(config):
    return {
        "active": bool(config.maintenance_mode),
        "message": config.maintenance_message,
        "estimated_end": config.estimated_end.isoformat() if config.estimated_end else None,
    }


@require_GET
def maintenance_status(request):
    config = SiteConfiguration.get()
    return JsonResponse(_serialize_config(config))


@require_POST
def maintenance_toggle(request):
    if not _is_admin(request.user):
        return JsonResponse({"detail": "forbidden"}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"detail": "invalid_json"}, status=400)

    if "active" not in payload:
        return JsonResponse({"detail": "active_required"}, status=400)

    active = bool(payload.get("active"))
    message = payload.get("message")
    estimated_end_raw = payload.get("estimated_end")

    config = SiteConfiguration.get()
    was_active = bool(config.maintenance_mode)
    config.maintenance_mode = active

    if isinstance(message, str) and message.strip():
        config.maintenance_message = message.strip()

    if estimated_end_raw:
        parsed = parse_datetime(estimated_end_raw)
        if parsed is None:
            return JsonResponse({"detail": "invalid_estimated_end"}, status=400)
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        config.estimated_end = parsed
    elif estimated_end_raw in ("", None):
        config.estimated_end = None

    if active and not was_active:
        config.maintenance_start = timezone.now()
    if not active:
        config.maintenance_start = None

    config.save()
    return JsonResponse(_serialize_config(config))
