import json
import math
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import OperationalError, ProgrammingError
from django.db.models import Avg, Count, FloatField, Max, Q
from django.db.models.functions import Coalesce, ExtractHour, TruncDate
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.core.views import serve_react

from .models import ChatMessage


def _safe_float(value, default=0.0):
    """Convert value to float, returning default for None/NaN/Inf."""
    if value is None:
        return default
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


@login_required
def chatbot_stats(request):
    return serve_react(request)



@login_required
@require_GET
def api_chatbot_stats(request):
    """GET /chatbot/api/stats/ - JSON stats for React admin page."""
    if getattr(request.user, "role", None) != "admin":
        return JsonResponse({"error": "Admin only."}, status=403)

    try:
        today   = timezone.now().date()
        last_7  = today - timedelta(days=7)
        last_30 = today - timedelta(days=30)

        base_qs   = ChatMessage.objects.select_related("session__user")
        month_qs  = base_qs.filter(created_at__date__gte=last_30)

        # --- Core KPIs ---
        questions_today  = int(base_qs.filter(created_at__date=today).count())
        questions_week   = int(base_qs.filter(created_at__date__gte=last_7).count())
        questions_month  = int(month_qs.count())

        # Duration: use 'duration' field directly (FloatField, default=0)
        dur_agg   = month_qs.aggregate(avg=Avg('duration'), mx=Max('duration'))
        avg_duration = _safe_float(dur_agg['avg'])
        max_duration = _safe_float(dur_agg['mx'])

        # Satisfaction: thumbs-up / (thumbs-up + thumbs-down)
        rated_qs       = base_qs.exclude(is_satisfied__isnull=True)
        evaluated_count = int(rated_qs.count())
        satisfied_count = int(rated_qs.filter(is_satisfied=True).count())
        satisfaction_rate = (
            round(satisfied_count * 100.0 / evaluated_count, 1)
            if evaluated_count > 0 else 0.0
        )

        # Out-of-scope answers
        unanswered = int(base_qs.filter(
            Q(answer__icontains="non disponible")
            | Q(answer__icontains="hors perimetre")
            | Q(answer__icontains="hors p\u00e9rim\u00e8tre")
        ).count())

        # --- Daily trend: last 30 days ---
        date_points = [today - timedelta(days=offset) for offset in range(29, -1, -1)]
        daily_counts = (
            month_qs
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Count("id"))
            .order_by("day")
        )
        daily_map = {item["day"]: int(item["total"]) for item in daily_counts}
        questions_per_day_labels = [d.strftime("%d/%m") for d in date_points]
        questions_per_day_values = [daily_map.get(d, 0) for d in date_points]

        # --- Peak hours: all messages grouped by hour ---
        hour_counts = (
            base_qs
            .annotate(hour=ExtractHour("created_at"))
            .values("hour")
            .annotate(total=Count("id"))
            .order_by("hour")
        )
        hour_map = {
            int(item["hour"]): int(item["total"])
            for item in hour_counts
            if item["hour"] is not None
        }
        peak_hours_labels = [f"{h:02d}h" for h in range(24)]
        peak_hours_values = [hour_map.get(h, 0) for h in range(24)]

        # --- Top 5 users by message count ---
        top_users_raw = (
            base_qs
            .values(
                "session__user__username",
                "session__user__first_name",
                "session__user__last_name",
            )
            .annotate(total=Count("id"))
            .order_by("-total")[:5]
        )
        top_users = []
        for row in top_users_raw:
            first = (row["session__user__first_name"] or "").strip()
            last  = (row["session__user__last_name"]  or "").strip()
            full  = f"{first} {last}".strip()
            top_users.append({
                "name":     full or row["session__user__username"],
                "username": row["session__user__username"],
                "total":    int(row["total"]),
            })

        # --- Last 10 thumbs-down messages ---
        bad_raw = (
            base_qs
            .filter(is_satisfied=False)
            .order_by("-created_at")[:10]
            .values(
                "created_at",
                "question",
                "session__user__username",
                "session__user__first_name",
                "session__user__last_name",
            )
        )
        unsatisfied_data = []
        for msg in bad_raw:
            first = (msg["session__user__first_name"] or "").strip()
            last  = (msg["session__user__last_name"]  or "").strip()
            full  = f"{first} {last}".strip() or msg["session__user__username"]
            unsatisfied_data.append({
                "date":     msg["created_at"].strftime("%d/%m %H:%M"),
                "user":     full,
                "question": (msg["question"] or "")[:90],
            })

    except (ProgrammingError, OperationalError) as e:
        return JsonResponse({"error": f"DB error: {e}"}, status=500)

    return JsonResponse({
        "questions_today":          questions_today,
        "questions_week":           questions_week,
        "questions_month":          questions_month,
        "avg_duration":             round(_safe_float(avg_duration), 1),
        "max_duration":             round(_safe_float(max_duration), 1),
        "satisfaction_rate":        round(_safe_float(satisfaction_rate), 1),
        "evaluated_count":          evaluated_count,
        "unanswered":               unanswered,
        "questions_per_day_labels": questions_per_day_labels,
        "questions_per_day_values": questions_per_day_values,
        "peak_hours_labels":        peak_hours_labels,
        "peak_hours_values":        peak_hours_values,
        "top_users":                top_users,
        "latest_unsatisfied":       unsatisfied_data,
    })
