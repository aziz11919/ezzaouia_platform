from django.urls import path
from . import views

app_name = 'forecasting'

urlpatterns = [
    path('field/', views.forecast_field, name='field'),
    path('well/<int:well_key>/', views.forecast_well, name='well'),
    path('wells/', views.forecast_all_wells, name='all_wells'),
    path('well-list/', views.list_wells, name='well_list'),
]
