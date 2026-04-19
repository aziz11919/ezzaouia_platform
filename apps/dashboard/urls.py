from django.urls import path
from . import views
from . import powerbi_views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('api/powerbi/',         powerbi_views.api_powerbi_list,   name='api_powerbi_list'),
    path('api/powerbi/<int:pk>/', powerbi_views.api_powerbi_detail, name='api_powerbi_detail'),
]