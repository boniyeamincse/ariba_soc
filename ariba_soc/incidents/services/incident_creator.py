import logging
from django.db import transaction
from django.utils import timezone
from alerts.models import Alert
from incidents.models import Incident, IncidentAlert, IncidentTimeline

logger = logging.getLogger(__name__)


class IncidentCreatorError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def create_incident_from_alerts(alert_ids, user, title, description, severity, priority,
                                business_unit='', affected_service='', business_impact='',
                                response_team='', owner=None, declaration_reason='',
                                primary_alert_id=None, detection_source=''):
    if not alert_ids:
        raise IncidentCreatorError('At least one alert is required')
    if len(alert_ids) > 50:
        raise IncidentCreatorError('Maximum 50 alerts per incident')

    with transaction.atomic():
        alerts = list(Alert.objects.select_for_update().filter(id__in=alert_ids))
        if len(alerts) != len(alert_ids):
            raise IncidentCreatorError('One or more alerts not found')

        incident = Incident(
            title=title,
            description=description,
            severity=severity,
            priority=priority,
            status='NEW',
            created_by=user,
            owner=owner,
            business_unit=business_unit,
            affected_service=affected_service,
            business_impact=business_impact,
            detection_source=detection_source,
            declaration_reason=declaration_reason,
            response_team=response_team,
            current_tier=user.analyst_profile.role if hasattr(user, 'analyst_profile') else 'L2',
        )
        incident.incident_number = Incident.generate_incident_number()
        incident.declared_at = timezone.now()
        incident.detected_at = alerts[0].alert_time if alerts else timezone.now()
        incident.save()

        primary_set = False
        for i, alert in enumerate(alerts):
            is_primary = (alert.id == primary_alert_id) or (i == 0 and not primary_alert_id)
            if is_primary:
                primary_set = True
            IncidentAlert.objects.create(
                incident=incident,
                alert=alert,
                linked_by=user,
                link_reason='Initial incident creation',
                is_primary=is_primary,
            )
            alert.is_incident_candidate = True
            alert.save(update_fields=['is_incident_candidate'])

        if not primary_set and alerts:
            ia = IncidentAlert.objects.filter(incident=incident).first()
            if ia:
                ia.is_primary = True
                ia.save(update_fields=['is_primary'])

        IncidentTimeline.objects.create(
            incident=incident,
            event_type='CREATED',
            actor=user,
            title='Incident created',
            description=f'Created from {len(alerts)} alert(s)',
        )

        for alert in alerts:
            IncidentTimeline.objects.create(
                incident=incident,
                event_type='ALERT_LINKED',
                actor=user,
                title=f'Alert {alert.alert_name} linked',
                description=f'Alert ID: {alert.id}',
                metadata={'alert_id': alert.id},
            )

    return incident


def link_alert_to_incident(incident, alert, user, reason=''):
    if incident.status in ('CLOSED',):
        raise IncidentCreatorError('Closed incidents cannot accept new alerts')
    with transaction.atomic():
        incident = Incident.objects.select_for_update().get(pk=incident.pk)
        if IncidentAlert.objects.filter(incident=incident, alert=alert).exists():
            raise IncidentCreatorError('Alert is already linked to this incident')
        IncidentAlert.objects.create(
            incident=incident,
            alert=alert,
            linked_by=user,
            link_reason=reason,
            is_primary=False,
        )
        IncidentTimeline.objects.create(
            incident=incident,
            event_type='ALERT_LINKED',
            actor=user,
            title=f'Alert {alert.alert_name} linked',
            description=reason,
            metadata={'alert_id': alert.id},
        )
    return incident


def unlink_alert_from_incident(incident, alert, user, reason=''):
    with transaction.atomic():
        incident = Incident.objects.select_for_update().get(pk=incident.pk)
        link = IncidentAlert.objects.filter(incident=incident, alert=alert).first()
        if not link:
            raise IncidentCreatorError('Alert is not linked to this incident')
        if link.is_primary:
            other = IncidentAlert.objects.filter(incident=incident).exclude(alert=alert).first()
            if not other:
                raise IncidentCreatorError('Cannot unlink the only primary alert')
            other.is_primary = True
            other.save(update_fields=['is_primary'])
        link.delete()
        IncidentTimeline.objects.create(
            incident=incident,
            event_type='ALERT_UNLINKED',
            actor=user,
            title=f'Alert {alert.alert_name} unlinked',
            description=reason,
            metadata={'alert_id': alert.id},
        )
    return incident
