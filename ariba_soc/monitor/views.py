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
    return JsonResponse(data)


@login_required
def wallboard_globe_api(request):
    return JsonResponse({'arcs': []})
