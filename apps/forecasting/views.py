import json
import numpy as np
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET

from apps.forecasting.forecaster import run_all_models, get_monthly_production, run_prophet
from apps.warehouse.models import DimWell


class _NumpyEncoder(json.JSONEncoder):
    """Converts numpy scalar types (int64, float64, bool_) to plain Python types."""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def _json(data, status=200):
    return JsonResponse(data, encoder=_NumpyEncoder, status=status)


@login_required
@require_GET
def forecast_field(request):
    """GET /api/forecasting/field/?kpi=oil&periods=60"""
    kpi = request.GET.get('kpi', 'oil')
    periods = int(request.GET.get('periods', 60))
    return _json(run_all_models(well_key=None, kpi=kpi, periods=periods))


@login_required
@require_GET
def forecast_well(request, well_key):
    """GET /api/forecasting/well/<well_key>/?kpi=oil&periods=60"""
    kpi = request.GET.get('kpi', 'oil')
    periods = int(request.GET.get('periods', 60))
    return _json(run_all_models(well_key=well_key, kpi=kpi, periods=periods))


@login_required
@require_GET
def forecast_all_wells(request):
    """GET /api/forecasting/wells/?kpi=oil — Prophet forecast for every active well."""
    kpi = request.GET.get('kpi', 'oil')

    wells = DimWell.objects.all().order_by('well_code')
    results = []

    for well in wells:
        df = get_monthly_production(well_key=well.well_key, kpi=kpi)
        if df.empty or len(df) < 12:
            continue

        prophet_result = run_prophet(df, periods=60)
        if not prophet_result:
            continue

        results.append({
            'well_key': well.well_key,
            'well_code': well.well_code,
            'well_name': well.libelle,
            'metrics': prophet_result['metrics'],
            'quarterly': prophet_result['quarterly'],
            'trend': prophet_result['trend_direction'],
            'forecast_2030': sum(
                f['yhat'] for f in prophet_result['forecast']
                if f['date'].startswith('2030')
            ),
        })

    results.sort(key=lambda x: x.get('forecast_2030', 0), reverse=True)
    return _json({'wells': results, 'kpi': kpi})


@login_required
@require_GET
def list_wells(request):
    """GET /api/forecasting/well-list/ — active wells for the React dropdown."""
    wells = DimWell.objects.all().order_by('well_code').values(
        'well_key', 'well_code', 'libelle'
    )
    return _json({'wells': list(wells)})
