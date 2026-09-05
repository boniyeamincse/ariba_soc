from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from ..permissions import require_incident_access
from ..models import Incident, IncidentNote, IncidentTimeline
from ..selectors import get_visible_incidents
from ..forms import NoteForm


@require_incident_access
def incident_notes(request, incident_number):
    incident = get_object_or_404(
        get_visible_incidents(request.user),
        incident_number=incident_number,
    )
    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            IncidentNote.objects.create(
                incident=incident,
                note_type=cd['note_type'],
                note=cd['note'],
                created_by=request.user,
            )
            IncidentTimeline.objects.create(
                incident=incident,
                event_type='NOTE_ADDED',
                actor=request.user,
                title=f'{cd["note_type"]} note added',
                description=cd['note'][:200],
            )
            messages.success(request, 'Note added')
    return redirect('incidents:detail', incident_number=incident_number)
