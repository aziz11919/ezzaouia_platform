from datetime import timedelta

from django.db.models import Avg, Sum
from django.utils import timezone

from apps.warehouse.models import FactDailyProduction


MAX_SUGGESTIONS = 5
PRIORITY_ORDER = {"critical": 0, "attention": 1, "normal": 2}
PRIORITY_ICON = {"critical": "🔴", "attention": "🟡", "normal": "🟢"}

GENERIC_FOLLOW_UPS = [
    "Compare the performance of the top 5 producing wells over 7 days",
    "Check the field average BSW trend for this week",
    "Analyze wells with the highest production variability",
    "Track the gap between actual production and weekly target",
    "Review the GOR trend of active wells",
]


def _make_item(text, priority="normal"):
    priority = priority if priority in PRIORITY_ORDER else "normal"
    return {
        "text": text,
        "priority": priority,
        "icon": PRIORITY_ICON[priority],
    }


def _safe_float(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _with_icon(items):
    out = []
    for item in items:
        priority = item.get("priority", "normal")
        out.append(
            {
                "text": item.get("text", ""),
                "priority": priority,
                "icon": PRIORITY_ICON.get(priority, "🟢"),
            }
        )
    return out


def _generic_suggestions():
    return [_make_item(text, "normal") for text in GENERIC_FOLLOW_UPS[:MAX_SUGGESTIONS]]


def generate_morning_suggestions():
    today = timezone.localdate()
    last_7_start = today - timedelta(days=6)
    prev_30_end = last_7_start - timedelta(days=1)
    prev_30_start = prev_30_end - timedelta(days=29)

    try:
        recent_qs = FactDailyProduction.objects.filter(
            datekey__fulldate__gte=last_7_start,
            datekey__fulldate__lte=today,
        )
        baseline_qs = FactDailyProduction.objects.filter(
            datekey__fulldate__gte=prev_30_start,
            datekey__fulldate__lte=prev_30_end,
        )

        recent_by_well = list(
            recent_qs.values("wellkey__wellcode").annotate(
                avg_bopd=Avg("dailyoilprodstbd"),
                avg_bsw=Avg("bsw"),
                avg_gor=Avg("gorscfstb"),
            )
        )
        baseline_by_well = list(
            baseline_qs.values("wellkey__wellcode").annotate(
                avg_bopd=Avg("dailyoilprodstbd"),
                avg_bsw=Avg("bsw"),
                avg_gor=Avg("gorscfstb"),
            )
        )
        recent_field = recent_qs.aggregate(total_oil=Sum("dailyoilprodstbd"))
        baseline_field = baseline_qs.aggregate(total_oil=Sum("dailyoilprodstbd"))
    except Exception:
        return _generic_suggestions()

    baseline_map = {row["wellkey__wellcode"]: row for row in baseline_by_well if row.get("wellkey__wellcode")}
    suggestions = []

    for row in recent_by_well:
        code = row.get("wellkey__wellcode")
        if not code:
            continue

        current_bopd = _safe_float(row.get("avg_bopd"))
        current_bsw = _safe_float(row.get("avg_bsw"))
        current_gor = _safe_float(row.get("avg_gor"))
        baseline_row = baseline_map.get(code, {})
        baseline_bopd = _safe_float(baseline_row.get("avg_bopd"))
        baseline_gor = _safe_float(baseline_row.get("avg_gor"))

        if baseline_bopd > 0:
            drop_pct = ((baseline_bopd - current_bopd) / baseline_bopd) * 100
            if drop_pct > 10:
                priority = "critical" if drop_pct >= 20 else "attention"
                suggestions.append(
                    _make_item(
                        f"Analyze {code}: production is down by {drop_pct:.0f}% this week",
                        priority,
                    )
                )

        if current_bsw > 70:
            priority = "critical" if current_bsw >= 80 else "attention"
            suggestions.append(
                _make_item(
                    f"Check water cut for {code}: BSW is {current_bsw:.0f}%, reservoir risk",
                    priority,
                )
            )

        if baseline_gor > 0 and current_gor > (2 * baseline_gor):
            factor = current_gor / baseline_gor
            priority = "critical" if factor >= 2.5 else "attention"
            suggestions.append(
                _make_item(
                    f"Abnormal GOR on {code}: {factor:.1f}x above normal, possible gas channeling?",
                    priority,
                )
            )

    recent_total = _safe_float(recent_field.get("total_oil"))
    baseline_total = _safe_float(baseline_field.get("total_oil"))
    if baseline_total > 0:
        objective_7d = (baseline_total / 30.0) * 7.0
        if objective_7d > 0:
            gap_pct = ((recent_total - objective_7d) / objective_7d) * 100
            if gap_pct <= -10:
                suggestions.append(
                    _make_item(
                        f"Field production below target: {abs(gap_pct):.0f}% negative gap this week",
                        "critical",
                    )
                )
            elif gap_pct <= -3:
                suggestions.append(
                    _make_item(
                        f"Field production below target: {abs(gap_pct):.0f}% requires correction",
                        "attention",
                    )
                )
            elif gap_pct >= 10:
                suggestions.append(
                    _make_item(
                        f"Field production above target: +{gap_pct:.0f}% this week",
                        "normal",
                    )
                )

    if not suggestions:
        return _generic_suggestions()

    dedup = {}
    for item in suggestions:
        text = item.get("text", "").strip()
        if not text:
            continue
        existing = dedup.get(text)
        if existing is None:
            dedup[text] = item
            continue
        if PRIORITY_ORDER[item["priority"]] < PRIORITY_ORDER[existing["priority"]]:
            dedup[text] = item

    sorted_items = sorted(
        dedup.values(),
        key=lambda x: (PRIORITY_ORDER.get(x["priority"], 9), x["text"]),
    )
    return _with_icon(sorted_items[:MAX_SUGGESTIONS])
