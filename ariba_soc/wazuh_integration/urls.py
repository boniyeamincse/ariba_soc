from django.urls import path
from . import views

app_name = 'wazuh_integration'

urlpatterns = [
    path('', views.wazuh_status, name='status'),
    path('sync/', views.wazuh_sync, name='sync'),
    path('logs/', views.sync_logs, name='logs'),
    path('config/update/', views.wazuh_config_update, name='config_update'),
    path('agents/', views.wazuh_agents, name='agents'),
    path('health/', views.wazuh_health, name='health'),
]
