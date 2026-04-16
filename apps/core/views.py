import os
from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def serve_react(request):
    """Serve the React SPA index.html for all frontend routes."""
    react_path = os.path.join(settings.BASE_DIR, 'static', 'react', 'index.html')
    if not os.path.exists(react_path):
        return HttpResponse(
            '<h1>Frontend not built</h1>'
            '<p>Run <code>npm run build</code> then <code>python manage.py collectstatic</code>.</p>',
            status=503,
            content_type='text/html',
        )
    return FileResponse(open(react_path, 'rb'), content_type='text/html')
