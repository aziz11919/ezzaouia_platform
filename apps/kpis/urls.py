from django.urls import path
from . import views

app_name = 'kpis'

urlpatterns = [
    path('summary/',    views.FieldSummaryView.as_view(),  name='summary'),
    path('wells/',      views.WellKpisView.as_view(),      name='wells'),
    path('trend/',      views.MonthlyTrendView.as_view(),  name='trend'),
    path('top/',        views.TopProducersView.as_view(),  name='top'),
    path('tests/',      views.WellTestView.as_view(),      name='tests'),
    path('cumulative/', views.CumulativeView.as_view(),    name='cumulative'),
]
