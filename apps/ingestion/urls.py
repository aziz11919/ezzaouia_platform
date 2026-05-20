from django.urls import path
from . import views

app_name = 'ingestion'

urlpatterns = [
    path('upload/', views.upload_view,    name='upload'),
    path('',        views.file_list_view, name='list'),
    # API JSON pour React
    path('recent/',                   views.api_recent_files, name='api_recent'),
    path('api-upload/',               views.api_upload,       name='api_upload'),
    path('api-status/<int:file_id>/', views.api_file_status,  name='api_status'),
]