from django.urls import path
from . import views

app_name = 'hunting'

urlpatterns = [
    path('live/', views.live_search_view, name='live_search'),
    path('api/search/', views.search_api, name='search_api'),
    path('api/event/<str:event_id>/', views.event_detail_api, name='event_detail'),
]
