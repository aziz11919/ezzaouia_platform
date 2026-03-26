"""
API REST KPIs — consommée par Power BI DirectQuery et le dashboard.
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .calculators import (
    get_field_production_summary,
    get_well_kpis,
    get_monthly_trend,
    get_well_test_kpis,
    get_top_producers,
    get_cumulative_production,
)

logger = logging.getLogger('apps')


class FieldSummaryView(APIView):
    """GET /api/kpis/summary/?year=2024&month=9"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year  = request.GET.get('year')
        month = request.GET.get('month')
        data  = get_field_production_summary(
            year=int(year)  if year  else None,
            month=int(month) if month else None,
        )
        return Response(data)


class WellKpisView(APIView):
    """GET /api/kpis/wells/?year=2024&well=1"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year     = request.GET.get('year')
        well_key = request.GET.get('well')
        data = get_well_kpis(
            well_key=int(well_key) if well_key else None,
            year=int(year) if year else None,
        )
        return Response(data)


class MonthlyTrendView(APIView):
    """GET /api/kpis/trend/?year=2024"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year     = request.GET.get('year')
        well_key = request.GET.get('well')
        data = get_monthly_trend(
            year=int(year) if year else None,
            well_key=int(well_key) if well_key else None,
        )
        return Response(data)


class TopProducersView(APIView):
    """GET /api/kpis/top/?year=2024&limit=5"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year  = request.GET.get('year')
        limit = int(request.GET.get('limit', 5))
        data  = get_top_producers(
            limit=limit,
            year=int(year) if year else None,
        )
        return Response(data)


class WellTestView(APIView):
    """GET /api/kpis/tests/?year=2024&well=1"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year     = request.GET.get('year')
        well_key = request.GET.get('well')
        data = get_well_test_kpis(
            well_key=int(well_key) if well_key else None,
            year=int(year) if year else None,
        )
        return Response(data)


class CumulativeView(APIView):
    """GET /api/kpis/cumulative/?well=1"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        well_key = request.GET.get('well')
        data = get_cumulative_production(
            well_key=int(well_key) if well_key else None,
        )
        # Convertir None en 0
        for k in data:
            if data[k] is None:
                data[k] = 0
        return Response(data)