from django.http import JsonResponse
from django.shortcuts import redirect

from apps.core.models import SiteConfiguration


class MaintenanceMiddleware:
    PUBLIC_ALLOWED_PREFIXES = (
        "/static/",
        "/media/",
        "/api/maintenance/status/",
        "/api/auth/login/",
        "/accounts/login/",
        "/accounts/api-login/",
        "/accounts/forgot-password/",
        "/accounts/api-forgot-password/",
        "/accounts/reset-password/",
        "/accounts/api-reset-password/",
        "/login",
        "/maintenance",
    )
    ADMIN_MAINTENANCE_PREFIXES = (
        "/administration/maintenance",
        "/api/maintenance/",
        "/accounts/logout/",
        "/accounts/api-logout/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or ""

        if any(path.startswith(prefix) for prefix in self.PUBLIC_ALLOWED_PREFIXES):
            return self.get_response(request)

        config = SiteConfiguration.get()
        if not config.maintenance_mode:
            return self.get_response(request)

        user = getattr(request, "user", None)
        is_admin = bool(
            user
            and user.is_authenticated
            and getattr(user, "role", "") == "admin"
        )
        if is_admin and any(
            path.startswith(prefix) for prefix in self.ADMIN_MAINTENANCE_PREFIXES
        ):
            return self.get_response(request)

        payload = {
            "detail": "maintenance",
            "message": config.maintenance_message,
            "estimated_end": config.estimated_end.isoformat() if config.estimated_end else None,
        }

        wants_json = (
            path.startswith("/api/")
            or "application/json" in (request.headers.get("Accept", "") or "")
            or "application/json" in (request.headers.get("Content-Type", "") or "")
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        )

        if wants_json:
            return JsonResponse(payload, status=503)

        if is_admin:
            return redirect("/administration/maintenance")

        return redirect("/maintenance")
