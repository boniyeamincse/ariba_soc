from django.urls import path
from . import views

app_name = 'wazuh_integration'

urlpatterns = [
    path('', views.wazuh_status, name='status'),
    path('sync/', views.wazuh_sync, name='sync'),
    path('logs/', views.sync_logs, name='logs'),
    path('config/update/', views.wazuh_config_update, name='config_update'),
    path('config/manager/update/', views.wazuh_manager_config_update, name='manager_config_update'),
    path('agents/', views.wazuh_agents, name='agents'),
    path('test-manager/', views.test_manager_connection, name='test_manager'),
    path('test-indexer/', views.test_indexer_connection, name='test_indexer'),
    path('health/', views.wazuh_health, name='health'),
    path('active-response/execute/', views.active_response_execute, name='active_response_execute'),
    path('active-response/history/', views.active_response_history, name='active_response_history'),
]

