from django.urls import path
from . import views

app_name = 'kpis'

urlpatterns = [
    path('summary/',     views.FieldSummaryView.as_view(),  name='summary'),
    path('wells/',       views.WellKpisView.as_view(),      name='wells'),
    path('trend/',       views.MonthlyTrendView.as_view(),  name='trend'),
    path('top-producers/', views.TopProducersView.as_view(), name='top-producers'),
    path('top/',         views.TopProducersView.as_view(),  name='top'),
    path('well-status/', views.WellStatusView.as_view(),    name='well-status'),
    path('tanks/',       views.TankLevelsView.as_view(),    name='tanks'),
]
