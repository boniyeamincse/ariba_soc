from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from alerts.models import Alert
from ..permissions import require_incident_access, incident_permission_required
from ..forms import IncidentCreateForm
from ..services.incident_creator import create_incident_from_alerts, IncidentCreatorError


@incident_permission_required('can_create_incident')
def incident_create(request):
    alert_ids = request.GET.getlist('alerts') or request.POST.getlist('alerts')
    alert_ids = [int(a) for a in alert_ids if a.isdigit()]
    alerts = Alert.objects.filter(id__in=alert_ids) if alert_ids else Alert.objects.none()

    if request.method == 'POST':
        form = IncidentCreateForm(request.POST)
        if form.is_valid():
            try:
                cd = form.cleaned_data
                incident = create_incident_from_alerts(
                    alert_ids=alert_ids,
                    user=request.user,
                    title=cd['title'],
                    description=cd['description'],
                    severity=cd['severity'],
                    priority=cd['priority'],
                    business_unit=cd.get('business_unit', ''),
                    affected_service=cd.get('affected_service', ''),
                    business_impact=cd.get('business_impact', ''),
                    response_team=cd.get('response_team', ''),
                    declaration_reason=cd.get('declaration_reason', ''),
                )
                messages.success(request, f'Incident {incident.incident_number} created')
                return redirect('incidents:detail', incident_number=incident.incident_number)
            except IncidentCreatorError as e:
                messages.error(request, str(e))
    else:
        form = IncidentCreateForm()

    return render(request, 'incidents/incident_create.html', {
        'form': form,
        'alerts': alerts,
        'alert_ids': alert_ids,
    })
