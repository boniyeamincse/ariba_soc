from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from ..permissions import require_incident_access
from ..models import Incident, IncidentTimeline
from ..selectors import get_visible_incidents
from ..workflow import ALLOWED_TRANSITIONS
from ..forms import NoteForm, TransitionForm


@require_incident_access
def incident_detail(request, incident_number):
    incident = get_object_or_404(
        get_visible_incidents(request.user),
        incident_number=incident_number,
    )
    timeline = incident.timeline.select_related('actor')[:50]
    notes = incident.notes.select_related('created_by')[:20]
    linked = incident.linked_alerts.select_related('alert', 'linked_by')[:50]
    allowed = ALLOWED_TRANSITIONS.get(incident.status, [])

    return render(request, 'incidents/incident_detail.html', {
        'incident': incident,
        'timeline': timeline,
        'notes': notes,
        'linked_alerts': linked,
        'allowed_transitions': allowed,
        'note_form': NoteForm(),
        'transition_form': TransitionForm(initial={'version': incident.version}),
    })
