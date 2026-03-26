from django.urls import path
from . import views

app_name = 'ingestion'

urlpatterns = [
    path('upload/', views.upload_view,    name='upload'),
    path('',        views.file_list_view, name='list'),
]