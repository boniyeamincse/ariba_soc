from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from ..permissions import require_incident_access
from ..models import Incident
from ..selectors import get_visible_incidents
from ..forms import TransitionForm
from ..workflow import (
    confirm_incident, start_investigation, start_containment,
    mark_eradicated, start_recovery, start_monitoring,
    resolve_incident, close_incident, reopen_incident,
    IncidentWorkflowError,
)


@require_incident_access
def incident_transition(request, incident_number):
    incident = get_object_or_404(
        get_visible_incidents(request.user),
        incident_number=incident_number,
    )
    if request.method == 'POST':
        action = request.POST.get('action', '')
        form = TransitionForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            version = cd['version']
            evidence = cd.get('evidence', '')
            try:
                fn_map = {
                    'confirm': lambda: confirm_incident(incident, request.user, version),
                    'investigate': lambda: start_investigation(incident, request.user, version),
                    'contain': lambda: start_containment(incident, request.user, version, evidence),
                    'eradicate': lambda: mark_eradicated(incident, request.user, version, evidence),
                    'recover': lambda: start_recovery(incident, request.user, version, evidence),
                    'monitor': lambda: start_monitoring(incident, request.user, version),
                    'resolve': lambda: resolve_incident(incident, request.user, version, evidence),
                    'close': lambda: close_incident(incident, request.user, version, evidence),
                    'reopen': lambda: reopen_incident(incident, request.user, version, evidence),
                }
                if action in fn_map:
                    fn_map[action]()
                    messages.success(request, f'Incident {action}d')
                else:
                    messages.error(request, f'Unknown action: {action}')
            except IncidentWorkflowError as e:
                messages.error(request, str(e))
    return redirect('incidents:detail', incident_number=incident_number)
