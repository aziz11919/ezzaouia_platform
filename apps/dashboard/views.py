import json
import datetime
from django.contrib.auth.decorators import login_required
from apps.core.views import serve_react

from apps.kpis.calculators import (
    get_field_production_summary,
    get_monthly_trend,
    get_top_producers,
)


@login_required
def home(request):
    # Frontend is handled by React SPA.
    return serve_react(request)

    # Legacy template context kept below for reference only.
    current_year = datetime.date.today().year
    year_param = request.GET.get('year')
    selected_year = int(year_param) if year_param and year_param.isdigit() else current_year

    summary = get_field_production_summary(year=selected_year)
    trend   = get_monthly_trend(year=selected_year)
    top5    = get_top_producers(limit=5, year=selected_year)

    trend_labels = [str(t.get('month_name', '')) for t in trend]
    trend_oil    = [float(t.get('total_oil') or 0) for t in trend]
    trend_bsw    = [float(t.get('avg_bsw')   or 0) for t in trend]
    top5_labels  = [w.get('well_code', '') for w in top5]
    top5_bopd    = [round(float(w.get('avg_bopd') or 0), 1) for w in top5]

    context = {
        'avg_bopd':           summary.get('avg_bopd', 0),
        'avg_bsw':            summary.get('avg_bsw', 0),
        'avg_gor':            summary.get('avg_gor', 0),
        'total_oil':          summary.get('total_oil_stbd', 0),
        'last_date':          summary.get('last_date'),
        'top_producers':      top5,
        'selected_year':      selected_year,
        'available_years':    [current_year, current_year - 1, current_year - 2],
        'trend_labels_json':  json.dumps(trend_labels),
        'trend_oil_json':     json.dumps(trend_oil),
        'trend_bsw_json':     json.dumps(trend_bsw),
        'top5_labels_json':   json.dumps(top5_labels),
        'top5_bopd_json':     json.dumps(top5_bopd),
    }
    return render(request, 'dashboard/overview.html', context)
