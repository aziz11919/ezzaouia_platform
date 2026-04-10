from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.generic import RedirectView
from django.views.static import serve

urlpatterns = [
    path('', RedirectView.as_view(url='/accounts/login/')),
    path('admin/',      admin.site.urls),
    path('accounts/',   include('apps.accounts.urls', namespace='accounts')),
    path('dashboard/',  include('apps.dashboard.urls', namespace='dashboard')),
    path('ingestion/',  include('apps.ingestion.urls')),
    path('bibliotheque/', include('apps.bibliotheque.urls', namespace='bibliotheque')),
    path('reports/', include('apps.reports.urls', namespace='reports')),
    path('chatbot/',    include('apps.chatbot.urls')),
    path('audit/',      include('apps.audit.urls', namespace='audit')),
    path('api/kpis/',   include('apps.kpis.urls')),
    path('api/warehouse/', include('apps.warehouse.urls')),
    # Media files — servis directement (WhiteNoise gère /static/)
    re_path(r'^media/(?P<path>.+)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
