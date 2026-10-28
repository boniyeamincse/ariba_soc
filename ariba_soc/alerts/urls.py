from django.urls import path
from . import views

app_name = 'alerts'

urlpatterns = [
    path('', views.alert_table, name='table'),
    path('board/', views.alert_board, name='board'),
    path('<int:alert_id>/', views.alert_detail, name='detail'),
    path('<int:alert_id>/edit/', views.alert_edit, name='edit'),
    path('<int:alert_id>/assign/', views.alert_assign, name='assign'),
    path('<int:alert_id>/enrich/', views.alert_enrich, name='enrich'),
    path('<int:alert_id>/pdf/', views.alert_pdf, name='pdf'),
    path('<int:alert_id>/bookmark/', views.alert_toggle_bookmark, name='bookmark'),
    path('<int:alert_id>/tags/', views.alert_set_tags, name='set_tags'),
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
    # Asset Directory (Phase 5)
    path('assets/', views.asset_directory, name='assets_list'),
    path('assets/create/', views.asset_create, name='asset_create'),
    path('assets/<int:asset_id>/edit/', views.asset_edit, name='asset_edit'),
    path('assets/<int:asset_id>/delete/', views.asset_delete, name='asset_delete'),
    path('assets/sync-wazuh/', views.asset_sync_wazuh, name='asset_sync_wazuh'),
    path('assets/recalculate-risk/', views.recalculate_all_alerts_risk, name='recalculate_risk'),
    # Phase 6: export + saved filters
    path('export/csv/', views.alert_export_csv, name='export_csv'),
    path('export/pdf/', views.alert_export_pdf, name='export_pdf'),
    path('saved-filters/save/', views.saved_filter_save, name='saved_filter_save'),
    path('saved-filters/<int:pk>/delete/', views.saved_filter_delete, name='saved_filter_delete'),
    # Phase 7: evidence attachments + watchers
    path('<int:alert_id>/attachments/upload/', views.alert_attachment_upload, name='attachment_upload'),
    path('attachments/<int:pk>/download/', views.alert_attachment_download, name='attachment_download'),
    path('attachments/<int:pk>/delete/', views.alert_attachment_delete, name='attachment_delete'),
    path('<int:alert_id>/watch/', views.alert_watcher_toggle, name='watcher_toggle'),
    path('<int:alert_id>/watchers/add/', views.alert_watcher_add, name='watcher_add'),
    path('<int:alert_id>/watchers/<int:user_id>/remove/', views.alert_watcher_remove, name='watcher_remove'),
    # Phase 8: related alerts + merge/split
    path('<int:alert_id>/related/', views.alert_related, name='related'),
    path('<int:alert_id>/merge/', views.alert_merge, name='merge'),
    path('<int:alert_id>/unmerge/', views.alert_unmerge, name='unmerge'),
    # Phase 9: false-positive feedback loop
    path('<int:alert_id>/report-fp/', views.alert_report_fp, name='report_fp'),
]
