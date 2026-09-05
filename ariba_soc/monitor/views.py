from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from . import services


@login_required
def wallboard(request):
    return render(request, 'monitor/wallboard.html')


@login_required
def wallboard_stats_api(request):
    data = {}
    data.update(services.wallboard_live_ops())
    data.update(services.wallboard_executive())
    return JsonResponse(data)


@login_required
def wallboard_globe_api(request):
    return JsonResponse({'arcs': services.resolve_globe_arcs()})
