from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render

from apps.audit.models import AuditLog
from apps.core.views import serve_react

from .pdf_generator import EzzaouiaReportGenerator


def _clean_year_month(raw_year, raw_month):
    now = datetime.now()
    year = now.year
    month = now.month

    if str(raw_year).isdigit():
        y = int(raw_year)
        if 2000 <= y <= 2100:
            year = y
    if str(raw_month).isdigit():
        m = int(raw_month)
        if 1 <= m <= 12:
            month = m

    return year, month


@login_required
def generate_report(request):
    allowed_roles = {"admin", "direction", "ingenieur"}
    role = getattr(request.user, "role", "")
    if role not in allowed_roles:
        return HttpResponseForbidden("Unauthorized access.")

    selected_year, selected_month = _clean_year_month(
        request.GET.get("year"),
        request.GET.get("month"),
    )

    should_download = request.GET.get("download") == "1"
    if should_download:
        generator = EzzaouiaReportGenerator()
        pdf_buffer = generator.generate_monthly_report(selected_year, selected_month, role)
        filename = f"EZZAOUIA_Report_{selected_month:02d}_{selected_year}.pdf"

        AuditLog.log(
            action=AuditLog.Action.EXPORT_PDF,
            user=request.user,
            request=request,
            details={
                "year": selected_year,
                "month": selected_month,
                "role": role,
                "module": "reports",
            },
        )

        response = HttpResponse(pdf_buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    return serve_react(request)
