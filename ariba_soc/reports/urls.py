from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_home, name='home'),
    path('mtta-mttr/', views.mtta_mttr_analytics, name='mtta_mttr'),
    path('mtta-mttr/export/csv/', views.export_mtta_mttr_csv, name='export_mtta_mttr_csv'),
    path('export/csv/', views.export_csv, name='export_csv'),
    path('export/excel/', views.export_excel, name='export_excel'),
    path('generate/<int:pk>/', views.generate_now, name='generate_now'),
    path('download/<int:pk>/', views.report_download, name='report_download'),
]
