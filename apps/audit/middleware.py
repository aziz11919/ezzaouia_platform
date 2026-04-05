import logging
import re
import time

from .models import AuditLog

logger = logging.getLogger("apps")


class AuditMiddleware:
    SKIP_PREFIXES = ("/static/", "/media/", "/admin/jsi18n/", "/favicon.ico")
    LOGIN_PATH = "/accounts/login/"
    LOGOUT_PATH = "/accounts/logout/"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started_at = time.perf_counter()
        response = self.get_response(request)

        try:
            self._log_request(request, response, started_at)
        except Exception as exc:
            logger.debug("Audit middleware error: %s", exc)

        return response

    def _log_request(self, request, response, started_at):
        path = (request.path or "").lower()
        if any(path.startswith(prefix) for prefix in self.SKIP_PREFIXES):
            return
        if response.status_code >= 400:
            return

        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        action, details = self._resolve_action(request, response, path, duration_ms)
        if not action:
            return

        AuditLog.log(action=action, request=request, details=details)

    def _resolve_action(self, request, response, path, duration_ms):
        if request.method == "POST" and re.match(r"^/chatbot/session/\d+/delete/?$", path):
            return (
                AuditLog.Action.DELETE_SESSION,
                {
                    "path": request.path,
                    "session_id": self._extract_session_id(path),
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )

        export_action = self._detect_export_action(request, response, path)
        if export_action:
            return (
                export_action,
                {
                    "path": request.path,
                    "status_code": response.status_code,
                    "query": request.META.get("QUERY_STRING", ""),
                    "duration_ms": duration_ms,
                },
            )

        content_type = (response.get("Content-Type") or "").lower()
        if (
            request.method == "GET"
            and "text/html" in content_type
            and not path.startswith(self.LOGIN_PATH)
            and not path.startswith(self.LOGOUT_PATH)
        ):
            return (
                AuditLog.Action.VIEW_PAGE,
                {
                    "path": request.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )

        return None, None

    def _detect_export_action(self, request, response, path):
        content_type = (response.get("Content-Type") or "").lower()
        export_format = (request.GET.get("format") or "").lower()

        if "application/pdf" in content_type:
            return AuditLog.Action.EXPORT_PDF

        if (
            "application/vnd.ms-excel" in content_type
            or "spreadsheetml" in content_type
            or "text/csv" in content_type
        ):
            return AuditLog.Action.EXPORT_EXCEL

        if "export" in path:
            if "pdf" in path or export_format == "pdf":
                return AuditLog.Action.EXPORT_PDF

            if (
                any(token in path for token in ("excel", "xlsx", "xls", "csv"))
                or export_format in {"excel", "xlsx", "xls", "csv"}
            ):
                return AuditLog.Action.EXPORT_EXCEL

        return None

    @staticmethod
    def _extract_session_id(path):
        match = re.search(r"/session/(\d+)/delete/?$", path)
        if not match:
            return None
        return int(match.group(1))
