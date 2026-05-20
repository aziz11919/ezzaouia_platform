import json

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        LOGIN = "LOGIN", "Login"
        LOGOUT = "LOGOUT", "Logout"
        UPLOAD_FILE = "UPLOAD_FILE", "Upload file"
        CHATBOT_QUESTION = "CHATBOT_QUESTION", "Chatbot question"
        EXPORT_PDF = "EXPORT_PDF", "Export PDF"
        EXPORT_EXCEL = "EXPORT_EXCEL", "Export Excel"
        VIEW_PAGE = "VIEW_PAGE", "View page"
        DELETE_SESSION = "DELETE_SESSION", "Delete session"
        SESSION_EXPIRED = "SESSION_EXPIRED", "Session expired"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=32, choices=Action.choices, db_index=True)
    details = models.TextField(blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Audit log"
        verbose_name_plural = "Audit logs"
        indexes = [
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self):
        username = self.user.username if self.user else "Anonymous"
        return f"{self.action} - {username} - {self.created_at:%Y-%m-%d %H:%M:%S}"

    @classmethod
    def get_client_ip(cls, request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR") or None

    @classmethod
    def log(
        cls,
        *,
        action,
        user=None,
        details="",
        request=None,
        ip_address=None,
        user_agent=None,
    ):
        if request is not None:
            if user is None and getattr(request, "user", None) is not None:
                if request.user.is_authenticated:
                    user = request.user
            if not ip_address:
                ip_address = cls.get_client_ip(request)
            if not user_agent:
                user_agent = request.META.get("HTTP_USER_AGENT", "")

        if user is not None and not getattr(user, "is_authenticated", False):
            user = None

        if isinstance(details, (dict, list)):
            details = json.dumps(details, ensure_ascii=False)

        details = (details or "")[:4000]
        user_agent = (user_agent or "")[:1000]

        try:
            return cls.objects.create(
                user=user,
                action=action,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception:
            return None

    @property
    def parsed_details(self):
        if hasattr(self, "_parsed_details_cache"):
            return self._parsed_details_cache

        raw = (self.details or "").strip()
        parsed = raw
        if raw.startswith("{") or raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
        self._parsed_details_cache = parsed
        return parsed

    @property
    def details_display(self):
        parsed = self.parsed_details
        if isinstance(parsed, dict):
            ignored = {"duration", "duration_seconds", "duration_ms"}
            parts = []
            for key, value in parsed.items():
                if key in ignored or value in (None, "", []):
                    continue
                label = key.replace("_", " ")
                if isinstance(value, list):
                    value = ", ".join(str(item) for item in value)
                parts.append(f"{label}: {value}")
            return " | ".join(parts) if parts else "-"
        return parsed if parsed else "-"

    @property
    def duration_seconds(self):
        parsed = self.parsed_details
        if not isinstance(parsed, dict):
            return None

        if isinstance(parsed.get("duration"), (int, float)):
            return float(parsed["duration"])
        if isinstance(parsed.get("duration_seconds"), (int, float)):
            return float(parsed["duration_seconds"])
        if isinstance(parsed.get("duration_ms"), (int, float)):
            return float(parsed["duration_ms"]) / 1000
        return None

    @property
    def duration_display(self):
        duration = self.duration_seconds
        if duration is None:
            return "-"
        return f"{duration:.2f}s"
