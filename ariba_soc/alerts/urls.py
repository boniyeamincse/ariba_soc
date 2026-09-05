from django.urls import path
from . import views

app_name = 'alerts'

urlpatterns = [
    path('', views.alert_table, name='table'),
    path('board/', views.alert_board, name='board'),
    path('<int:alert_id>/', views.alert_detail, name='detail'),
    path('<int:alert_id>/edit/', views.alert_edit, name='edit'),
    path('<int:alert_id>/assign/', views.alert_assign, name='assign'),
    path('<int:alert_id>/comment/', views.alert_add_comment, name='add_comment'),
    path('<int:alert_id>/claim/', views.alert_claim, name='claim'),
    path('<int:alert_id>/escalate/', views.alert_escalate, name='escalate'),
    path('<int:alert_id>/accept-escalation/', views.alert_escalation_accept, name='escalation_accept'),
    path('<int:alert_id>/return-escalation/', views.alert_escalation_return, name='escalation_return'),
    path('<int:alert_id>/resolve/', views.alert_resolve, name='resolve'),
    path('<int:alert_id>/close/', views.alert_close, name='close'),
    path('<int:alert_id>/reopen/', views.alert_reopen, name='reopen'),
    path('<int:alert_id>/create-incident/', views.alert_create_incident, name='create_incident'),
    path('<int:alert_id>/archive/', views.alert_archive, name='archive'),
    path('my-alerts/', views.my_alerts, name='my_alerts'),
    path('bulk-action/', views.alert_bulk_action, name='bulk_action'),
    path('api/alerts/', views.alerts_api, name='alerts_api'),
    path('api/alerts/<int:alert_id>/move/', views.alert_move_api, name='alert_move_api'),
    path('notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
]
