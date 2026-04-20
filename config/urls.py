from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from apps.audit import views as audit_views
from apps.bibliotheque import views as bibliotheque_views
from apps.core.powerbi_views import powerbi_reports
from apps.core.views import serve_react
from apps.dashboard import powerbi_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('dashboard/', include('apps.dashboard.urls', namespace='dashboard')),
    path('ingestion/', include('apps.ingestion.urls')),
    path('bibliotheque/', include('apps.bibliotheque.urls', namespace='bibliotheque')),
    path('reports/', include('apps.reports.urls', namespace='reports')),
    path('chatbot/', include('apps.chatbot.urls')),
    path('audit/', include('apps.audit.urls', namespace='audit')),
    path('api/kpis/', include('apps.kpis.urls')),
    path('api/warehouse/', include('apps.warehouse.urls')),
    path('api/library/documents/', bibliotheque_views.api_documents, name='api_library_documents'),
    path('api/library/documents/<int:pk>/delete/', bibliotheque_views.api_delete_document, name='api_library_delete'),
    path('api/audit/logs/', audit_views.api_logs, name='api_audit_logs'),
    path('api/powerbi/reports/', powerbi_reports, name='api_powerbi_reports'),
    path('api/powerbi/', powerbi_views.api_powerbi_list, name='api_powerbi_list'),
    path('api/powerbi/<int:pk>/', powerbi_views.api_powerbi_detail, name='api_powerbi_detail'),
    re_path(r'^media/(?P<path>.+)$', serve, {'document_root': settings.MEDIA_ROOT}),
    path('', serve_react),
    re_path(r'^(?!admin/|api/|media/|static/).*$' , serve_react),
]
