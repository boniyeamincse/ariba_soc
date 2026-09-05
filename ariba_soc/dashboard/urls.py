from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('l1/', views.dashboard_l1, name='l1'),
    path('l2/', views.dashboard_l2, name='l2'),
    path('l3/', views.dashboard_l3, name='l3'),
    path('manager/', views.dashboard_manager, name='manager'),
    path('api/stats/', views.dashboard_stats_api, name='stats_api'),
]
