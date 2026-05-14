import json
import numpy as np
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET

from apps.forecasting.forecaster import (
    run_all_models,
    get_monthly_production,
    run_prophet,
    run_sarima,
    run_arima,
    run_holt_winters,
)
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


def _trend_from_forecast_points(points):
    values = [p.get('yhat') for p in points if p.get('yhat') is not None]
    if len(values) < 2:
        return 'increasing'
    return 'declining' if float(values[-1]) < float(values[0]) else 'increasing'


def _run_best_available_model(df, periods=60):
    # Keep Prophet as primary model, but gracefully fall back when it fails.
    prophet_result = run_prophet(df, periods=periods)
    if prophet_result:
        return prophet_result

    for runner in (run_sarima, run_arima, run_holt_winters):
        fallback_result = runner(df, periods=periods)
        if fallback_result:
            return fallback_result

    return None


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
    try:
        well = DimWell.objects.get(well_key=well_key)
    except DimWell.DoesNotExist:
        return _json({'error': 'Well not found.'}, status=404)

    if well.closed == 'Y':
        return _json(
            {'error': f'Well {well.well_code} is closed. Forecasting is not available.'},
            status=400,
        )

    return _json(run_all_models(well_key=well_key, kpi=kpi, periods=periods))


@login_required
@require_GET
def forecast_all_wells(request):
    """GET /api/forecasting/wells/?kpi=oil - forecast for every active well."""
    kpi = request.GET.get('kpi', 'oil')
    periods = int(request.GET.get('periods', 60))

    wells = DimWell.objects.exclude(closed='Y').order_by('well_code')
    results = []

    for well in wells:
        df = get_monthly_production(well_key=well.well_key, kpi=kpi)
        if df.empty or len(df) < 12:
            continue

        model_result = _run_best_available_model(df, periods=periods)
        if not model_result:
            continue

        forecast_points = model_result.get('forecast') or []
        trend = model_result.get('trend_direction') or _trend_from_forecast_points(forecast_points)
        horizon_sum = sum(float(f.get('yhat', 0) or 0) for f in forecast_points)
        forecast_2030 = sum(
            float(f.get('yhat', 0) or 0)
            for f in forecast_points
            if str(f.get('date', '')).startswith('2030')
        )

        results.append(
            {
                'well_key': well.well_key,
                'well_code': well.well_code,
                'well_name': well.libelle,
                'metrics': model_result.get('metrics') or {},
                'quarterly': model_result.get('quarterly') or [],
                'trend': trend,
                'model': model_result.get('model', 'Unknown'),
                'forecast_horizon': horizon_sum,
                'forecast_2030': forecast_2030,
            }
        )

    results.sort(key=lambda x: x.get('forecast_horizon', 0), reverse=True)
    return _json({'wells': results, 'kpi': kpi, 'periods': periods})


@login_required
@require_GET
def list_wells(request):
    """GET /api/forecasting/well-list/ - active wells for the React dropdown."""
    wells = DimWell.objects.exclude(closed='Y').order_by('well_code').values(
        'well_key', 'well_code', 'libelle'
    )
    return _json({'wells': list(wells)})
