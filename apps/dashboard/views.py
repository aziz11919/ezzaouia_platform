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
    return serve_react(request)

