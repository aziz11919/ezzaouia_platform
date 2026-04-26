import json
import os

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

CONFIG_FILE = '/app/data/powerbi_config.json'

DEFAULT_REPORTS = [
    {
        'id': 'report_1',
        'title': 'EZZAOUIA Dashboard',
        'embed_url': '',
        'description': 'Production KPIs MARETAP',
    }
]


@login_required
@csrf_exempt
@require_http_methods(['GET', 'POST'])
def powerbi_reports(request):
    if request.method == 'GET':
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, encoding='utf-8') as f:
                    reports = json.load(f)
            else:
                reports = DEFAULT_REPORTS
            return JsonResponse({'reports': reports})
        except Exception:
            return JsonResponse({'reports': DEFAULT_REPORTS})

    if not request.user.is_staff:
        return JsonResponse({'error': 'Admin only'}, status=403)
    try:
        data = json.loads(request.body)
        reports = data.get('reports', [])
        os.makedirs('/app/data', exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
