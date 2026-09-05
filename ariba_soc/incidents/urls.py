from django.urls import path
from .views import list, detail, create, assignment, transition, notes

app_name = 'incidents'

urlpatterns = [
    path('', list.incident_list, name='list'),
    path('create/', create.incident_create, name='create'),
    path('<str:incident_number>/', detail.incident_detail, name='detail'),
    path('<str:incident_number>/assign/', assignment.incident_assign, name='assign'),
    path('<str:incident_number>/transition/', transition.incident_transition, name='transition'),
    path('<str:incident_number>/notes/', notes.incident_notes, name='notes'),
]
