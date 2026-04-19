from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .powerbi_models import PowerBIReport
from .powerbi_serializers import PowerBIReportSerializer


def _visible_qs(user):
    role = getattr(user, 'role', '')
    return PowerBIReport.objects.filter(
        active=True
    ).filter(Q(role='all') | Q(role=role))


@login_required
@require_GET
def api_powerbi_list(request):
    reports = _visible_qs(request.user)
    data = PowerBIReportSerializer(reports, many=True).data
    return JsonResponse({'reports': list(data)})


@login_required
@require_GET
def api_powerbi_detail(request, pk):
    try:
        report = _visible_qs(request.user).get(pk=pk)
    except PowerBIReport.DoesNotExist:
        return JsonResponse({'error': 'Not found.'}, status=404)
    return JsonResponse({'report': PowerBIReportSerializer(report).data})
