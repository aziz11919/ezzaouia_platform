from django.urls import path
from . import views

app_name = 'bibliotheque'

urlpatterns = [
    path('',              views.bibliotheque,    name='index'),
    path('<int:pk>/delete/', views.delete_document, name='delete'),
]
