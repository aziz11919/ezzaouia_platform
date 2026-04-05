from urllib.parse import quote

from django.contrib import auth, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone


class SessionTimeoutMiddleware:
    timeout_seconds = 1800
    session_key = "last_activity"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now_ts = int(timezone.now().timestamp())
            last_activity = request.session.get(self.session_key)

            if last_activity is not None:
                try:
                    inactivity_seconds = now_ts - int(last_activity)
                except (TypeError, ValueError):
                    inactivity_seconds = 0

                if inactivity_seconds > self.timeout_seconds:
                    user = request.user
                    username = user.get_username()

                    auth.logout(request)
                    messages.warning(
                        request,
                        "Session expiree apres 30 min d'inactivite. Reconnectez-vous.",
                    )
                    self._log_session_expired(
                        request=request,
                        user=user,
                        username=username,
                        inactivity_seconds=inactivity_seconds,
                    )

                    login_url = reverse("accounts:login")
                    return redirect(f"{login_url}?next={quote(request.path)}")

            request.session[self.session_key] = now_ts

        response = self.get_response(request)
        return response

    @staticmethod
    def _log_session_expired(*, request, user, username, inactivity_seconds):
        try:
            from apps.audit.models import AuditLog
        except Exception:
            return

        action = getattr(AuditLog.Action, "SESSION_EXPIRED", "SESSION_EXPIRED")
        AuditLog.log(
            action=action,
            user=user,
            request=request,
            details={
                "username": username,
                "path": request.path,
                "inactivity_seconds": inactivity_seconds,
            },
        )
