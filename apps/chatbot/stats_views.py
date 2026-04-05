import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import OperationalError, ProgrammingError
from django.db.models import Avg, Count, FloatField, Max, Q
from django.db.models.functions import Coalesce, ExtractHour, TruncDate
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import ChatMessage


@login_required
def chatbot_stats(request):
    if getattr(request.user, "role", None) != "admin":
        messages.error(request, "Acces reserve aux administrateurs.")
        return redirect("dashboard:home")

    try:
        now = timezone.now()
        today = timezone.localdate()
        start_week = now - timedelta(days=7)
        start_month = now - timedelta(days=30)

        all_messages = ChatMessage.objects.select_related("session__user")
        month_messages = all_messages.filter(created_at__gte=start_month)

        questions_today = all_messages.filter(created_at__date=today).count()
        questions_week = all_messages.filter(created_at__gte=start_week).count()
        questions_month = month_messages.count()

        duration_expr = Coalesce("duration_seconds", "duration", output_field=FloatField())
        duration_stats = month_messages.aggregate(
            avg_duration=Avg(duration_expr),
            max_duration=Max(duration_expr),
        )
        avg_duration = float(duration_stats["avg_duration"] or 0)
        max_duration = float(duration_stats["max_duration"] or 0)

        evaluated_qs = all_messages.exclude(is_satisfied__isnull=True)
        evaluated_count = evaluated_qs.count()
        satisfied_count = evaluated_qs.filter(is_satisfied=True).count()
        satisfaction_rate = round((satisfied_count * 100.0 / evaluated_count), 2) if evaluated_count else 0.0

        date_points = [today - timedelta(days=offset) for offset in range(29, -1, -1)]
        daily_counts = (
            month_messages
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Count("id"))
            .order_by("day")
        )
        daily_map = {item["day"]: item["total"] for item in daily_counts}
        questions_per_day = [{"date": d.strftime("%d/%m"), "count": daily_map.get(d, 0)} for d in date_points]

        top_users_raw = (
            all_messages
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
            first_name = (row["session__user__first_name"] or "").strip()
            last_name = (row["session__user__last_name"] or "").strip()
            full_name = f"{first_name} {last_name}".strip()
            top_users.append(
                {
                    "name": full_name or row["session__user__username"],
                    "username": row["session__user__username"],
                    "total": row["total"],
                }
            )

        hour_counts = (
            month_messages
            .annotate(hour=ExtractHour("created_at"))
            .values("hour")
            .annotate(total=Count("id"))
            .order_by("hour")
        )
        hour_map = {int(item["hour"]): item["total"] for item in hour_counts if item["hour"] is not None}
        peak_hours = [{"hour": hour, "count": hour_map.get(hour, 0)} for hour in range(24)]

        unanswered_qs = all_messages.filter(
            Q(answer__icontains="non disponible")
            | Q(answer__icontains="hors perimetre")
            | Q(answer__icontains="hors p\u00e9rim\u00e8tre")
        ).order_by("-created_at")
        unanswered = unanswered_qs.count()

        latest_unsatisfied = (
            all_messages
            .filter(is_satisfied=False)
            .select_related("session__user")
            .order_by("-created_at")[:10]
        )
    except (ProgrammingError, OperationalError):
        messages.error(
            request,
            "Base non migree pour les stats chatbot. Executez: python manage.py migrate chatbot",
        )
        return redirect("chatbot:chat")

    context = {
        "questions_today": questions_today,
        "questions_week": questions_week,
        "questions_month": questions_month,
        "avg_duration": avg_duration,
        "max_duration": max_duration,
        "satisfaction_rate": satisfaction_rate,
        "evaluated_count": evaluated_count,
        "unanswered": unanswered,
        "questions_per_day": questions_per_day,
        "top_users": top_users,
        "peak_hours": peak_hours,
        "latest_unsatisfied": latest_unsatisfied,
        "unanswered_messages": unanswered_qs[:20],
        "questions_per_day_labels_json": json.dumps([item["date"] for item in questions_per_day]),
        "questions_per_day_values_json": json.dumps([item["count"] for item in questions_per_day]),
        "peak_hours_labels_json": json.dumps([f"{item['hour']:02d}h" for item in peak_hours]),
        "peak_hours_values_json": json.dumps([item["count"] for item in peak_hours]),
    }
    return render(request, "chatbot/stats.html", context)
