from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render


@login_required
def wallboard(request):
    return render(request, 'monitor/wallboard.html')


@login_required
def wallboard_stats_api(request):
    return JsonResponse({})


@login_required
def wallboard_globe_api(request):
    return JsonResponse({'arcs': []})
