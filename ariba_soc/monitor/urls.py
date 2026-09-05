from django.urls import path
from . import views

app_name = 'monitor'

urlpatterns = [
    path('dashboard/', views.wallboard, name='wallboard'),
    path('api/stats/', views.wallboard_stats_api, name='stats_api'),
    path('api/globe/', views.wallboard_globe_api, name='globe_api'),
]
