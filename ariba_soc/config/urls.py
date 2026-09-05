from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('', include('alerts.urls')),
    path('wazuh/', include('wazuh_integration.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('monitor/', include('monitor.urls')),
    path('reports/', include('reports.urls')),
    path('audit/', include('audit.urls')),
    path('settings/', include('settings_manager.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

