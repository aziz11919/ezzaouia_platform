"""
API REST KPIs — consommée par Power BI DirectQuery et le dashboard.
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .calculators import (
    get_field_production_summary,
    get_well_kpis,
    get_monthly_trend,
    get_well_status_kpis,
    get_top_producers,
    get_tank_levels,
)

logger = logging.getLogger('apps')


class FieldSummaryView(APIView):
    """GET /api/kpis/summary/?year=2024&month=9"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year  = request.GET.get('year')
        month = request.GET.get('month')
        data  = get_field_production_summary(
            year=int(year)   if year  else None,
            month=int(month) if month else None,
        )
        # Contract for frontend: expose both `total_oil` and legacy `total_oil_stbd`.
        if 'total_oil' not in data:
            data['total_oil'] = data.get('total_oil_stbd', 0)
        return Response(data)


class WellKpisView(APIView):
    """GET /api/kpis/wells/?year=2024&well=1"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year     = request.GET.get('year')
        month    = request.GET.get('month')
        well_key = request.GET.get('well')
        data = get_well_kpis(
            well_key=int(well_key) if well_key else None,
            year=int(year)   if year  else None,
            month=int(month) if month else None,
        )
        return Response(data)


class MonthlyTrendView(APIView):
    """GET /api/kpis/trend/?year=2024&well=1"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year       = request.GET.get('year')
        well_key   = request.GET.get('well')
        year_start = request.GET.get('year_start')
        year_end   = request.GET.get('year_end')
        data = get_monthly_trend(
            year=int(year)             if year       else None,
            well_key=int(well_key)     if well_key   else None,
            year_start=int(year_start) if year_start else None,
            year_end=int(year_end)     if year_end   else None,
        )
        return Response(data)


class TopProducersView(APIView):
    """GET /api/kpis/top-producers/?year=2024&month=9&limit=5"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year  = request.GET.get('year')
        month = request.GET.get('month')
        limit = int(request.GET.get('limit', 5))
        data  = get_top_producers(
            limit=limit,
            year=int(year)   if year  else None,
            month=int(month) if month else None,
        )
        return Response(data)


class WellStatusView(APIView):
    """
    GET /api/kpis/well-status/?year=2024&month=9&well=1
    Retourne ProdHours, BSW, GOR, pressions depuis DimWellStatus.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year     = request.GET.get('year')
        month    = request.GET.get('month')
        well_key = request.GET.get('well')
        data = get_well_status_kpis(
            well_key=int(well_key) if well_key else None,
            year=int(year)   if year  else None,
            month=int(month) if month else None,
        )
        return Response(data)


class TankLevelsView(APIView):
    """
    GET /api/kpis/tanks/?year=2024&month=9&tank=1
    Retourne le niveau des tanks (VolumeBBLS) par date.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year       = request.GET.get('year')
        month      = request.GET.get('month')
        tank_key   = request.GET.get('tank')
        date_start = request.GET.get('date_start')
        date_end   = request.GET.get('date_end')
        data = get_tank_levels(
            tank_key=int(tank_key) if tank_key else None,
            year=int(year)   if year  else None,
            month=int(month) if month else None,
            date_start=date_start or None,
            date_end=date_end or None,
        )
        return Response(data)
