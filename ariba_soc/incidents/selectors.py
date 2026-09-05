from django.db.models import Q
from .models import Incident


def get_visible_incidents(user):
    if not hasattr(user, 'analyst_profile'):
        return Incident.objects.none()
    role = user.analyst_profile.role
    if role == 'MONITOR':
        return Incident.objects.none()
    if role == 'VIEWER':
        return Incident.objects.filter(owner=user)
    if role == 'L1':
        from alerts.models import Alert
        my_alert_ids = Alert.objects.filter(assignee=user).values_list('id', flat=True)
        return Incident.objects.filter(linked_alerts__alert_id__in=my_alert_ids).distinct()
    return Incident.objects.all()


def get_incident_by_number(incident_number):
    return Incident.objects.get(incident_number=incident_number)
