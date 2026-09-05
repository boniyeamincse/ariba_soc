from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('api/stats/', views.dashboard_stats_api, name='stats_api'),
]
