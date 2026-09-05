from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from ..permissions import require_incident_access
from ..models import Incident, IncidentTimeline
from ..selectors import get_visible_incidents


@require_incident_access
def incident_assign(request, incident_number):
    incident = get_object_or_404(
        get_visible_incidents(request.user),
        incident_number=incident_number,
    )
    if request.method == 'POST':
        owner_id = request.POST.get('owner')
        team = request.POST.get('response_team', '')
        try:
            owner = User.objects.get(id=owner_id) if owner_id else None
            old_owner = incident.owner
            incident.owner = owner
            if team:
                incident.response_team = team
            incident.version += 1
            incident.save(update_fields=['owner', 'response_team', 'version', 'updated_at'])
            IncidentTimeline.objects.create(
                incident=incident,
                event_type='ASSIGNED',
                actor=request.user,
                title=f'Assigned to {owner.username if owner else "unassigned"}',
                from_value=old_owner.username if old_owner else '',
                to_value=owner.username if owner else '',
            )
            messages.success(request, 'Incident assigned')
        except User.DoesNotExist:
            messages.error(request, 'User not found')
    return redirect('incidents:detail', incident_number=incident_number)
