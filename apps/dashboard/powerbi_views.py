from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods
import json

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


def _admin_only(request):
    return bool(getattr(request.user, 'is_admin', False) or getattr(request.user, 'role', '') == 'admin')


@login_required
@require_http_methods(["POST"])
def api_powerbi_create(request):
    if not _admin_only(request):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    serializer = PowerBIReportSerializer(data=data)
    if not serializer.is_valid():
        return JsonResponse({'errors': serializer.errors}, status=400)

    report = serializer.save()
    return JsonResponse({'success': True, 'report': PowerBIReportSerializer(report).data}, status=201)


@login_required
@require_http_methods(["PUT", "PATCH"])
def api_powerbi_update(request, pk):
    if not _admin_only(request):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        report = PowerBIReport.objects.get(pk=pk)
    except PowerBIReport.DoesNotExist:
        return JsonResponse({'error': 'Not found.'}, status=404)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    serializer = PowerBIReportSerializer(report, data=data, partial=True)
    if not serializer.is_valid():
        return JsonResponse({'errors': serializer.errors}, status=400)

    report = serializer.save()
    return JsonResponse({'success': True, 'report': PowerBIReportSerializer(report).data})


@login_required
@require_http_methods(["DELETE"])
def api_powerbi_delete(request, pk):
    if not _admin_only(request):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        report = PowerBIReport.objects.get(pk=pk)
    except PowerBIReport.DoesNotExist:
        return JsonResponse({'error': 'Not found.'}, status=404)

    report.delete()
    return JsonResponse({'success': True})
