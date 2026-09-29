from django.shortcuts import render
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from ..permissions import require_incident_access
from ..selectors import get_visible_incidents
from ..forms import IncidentFilterForm
from ..services.metrics import get_incident_metrics


@require_incident_access
def incident_list(request):
    form = IncidentFilterForm(request.GET)
    qs = get_visible_incidents(request.user)
    if form.is_valid():
        if form.cleaned_data.get('status'):
            qs = qs.filter(status=form.cleaned_data['status'])
        if form.cleaned_data.get('severity'):
            qs = qs.filter(severity=form.cleaned_data['severity'])
        if form.cleaned_data.get('priority'):
            qs = qs.filter(priority=form.cleaned_data['priority'])
        if form.cleaned_data.get('search'):
            qs = qs.filter(title__icontains=form.cleaned_data['search'])

    qs = qs.select_related('owner', 'created_by').prefetch_related('linked_alerts').order_by('-created_at')
    
    paginator = Paginator(qs, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'incidents/incident_list.html', {
        'form': form,
        'page_obj': page_obj,
        'total': paginator.count,
    })
