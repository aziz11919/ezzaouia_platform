from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
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
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
