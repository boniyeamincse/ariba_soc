from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from .models import AnalystProfile
from .forms import ProfileForm


@login_required
def role_redirect(request):
    profile = getattr(request.user, 'analyst_profile', None)
    if not profile:
        return redirect('alerts:table')
    role_dashboard_map = {
        'L1': 'dashboard:l1',
        'L2': 'dashboard:l2',
        'L3': 'dashboard:l3',
        'SOC_MGR': 'dashboard:manager',
        'ADMIN': 'dashboard:manager',
        'MONITOR': 'monitor:wallboard',
        'VIEWER': 'dashboard:l1',
        'SOC_ENG': 'dashboard:l3',
    }
    url_name = role_dashboard_map.get(profile.role, 'alerts:table')
    try:
        return redirect(reverse(url_name))
    except Exception:
        return redirect('alerts:table')


@login_required
def profile_view(request):
    profile = request.user.analyst_profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = ProfileForm(instance=profile, user=request.user)
    from alerts.models import Alert
    closed_count = Alert.objects.filter(assignee=request.user, status='Closed').count()
    return render(request, 'ariba_soc/profile.html', {
        'profile': profile, 'form': form, 'closed_count': closed_count
    })


@login_required
def user_list(request):
    profiles = AnalystProfile.objects.select_related('user').all()
    return render(request, 'ariba_soc/user_list.html', {'profiles': profiles})
