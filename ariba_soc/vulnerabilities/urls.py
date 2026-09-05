from django.urls import path
from . import views

app_name = 'vulnerabilities'

urlpatterns = [
    path('', views.overview, name='overview'),
    path('inventory/', views.inventory, name='inventory'),
    path('assets/', views.affected_assets, name='affected_assets'),
    path('cves/', views.cve_list, name='cve_list'),
    path('sync/', views.sync_from_wazuh, name='sync'),
    path('<str:key>/', views.detail, name='detail'),
    path('<str:key>/assign/', views.assign_view, name='assign'),
    path('<str:key>/remediate/', views.remediate_view, name='remediate'),
    path('<str:key>/accept-risk/', views.accept_risk_view, name='accept_risk'),
    path('<str:key>/verify/', views.verify_view, name='verify'),
    path('<str:key>/reopen/', views.reopen_view, name='reopen'),
    path('<str:key>/false-positive/', views.false_positive_view, name='false_positive'),
]
