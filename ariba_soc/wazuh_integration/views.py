from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import WazuhSyncLog, WazuhConfiguration
from .forms import WazuhConfigurationForm
from .services import WazuhClient


@login_required
def wazuh_status(request):
    config = WazuhConfiguration.objects.first()
    sync_logs = WazuhSyncLog.objects.all()[:20]
    
    # Initialize form with existing config or empty
    if config:
        form = WazuhConfigurationForm(instance=config)
    else:
        form = WazuhConfigurationForm()
        
    return render(request, 'ariba_soc/wazuh_status.html', {
        'config': config,
        'sync_logs': sync_logs,
        'form': form,
    })


@login_required
def wazuh_config_update(request):
    if request.method == 'POST':
        config = WazuhConfiguration.objects.first()
        if config:
            form = WazuhConfigurationForm(request.POST, instance=config)
        else:
            form = WazuhConfigurationForm(request.POST)
            
        if form.is_valid():
            form.save()
            messages.success(request, "Wazuh configuration updated successfully.")
        else:
            messages.error(request, "Failed to update configuration. Please check the form errors.")
    return redirect('wazuh_integration:status')


@login_required
def wazuh_agents(request):
    agents = []
    error = None
    try:
        client = WazuhClient()
        response = client.fetch_agents()
        agents = response.get('data', {}).get('affected_items', [])
        # Some Wazuh API versions use different structure, handle fallback
        if not agents and 'data' in response and 'items' in response['data']:
            agents = response['data']['items']
    except Exception as e:
        error = f"Failed to fetch agents: {str(e)}"
        
    return render(request, 'ariba_soc/wazuh_agents.html', {
        'agents': agents,
        'error': error
    })


@login_required
def wazuh_sync(request):
    if request.method == 'POST':
        from .services import fetch_wazuh_alerts
        try:
            result = fetch_wazuh_alerts()
            messages.success(request, f"Sync completed: {result.get('created', 0)} new alerts.")
        except Exception as e:
            messages.error(request, f"Sync failed: {str(e)}")
    return redirect('wazuh_integration:status')


@login_required
def sync_logs(request):
    logs = WazuhSyncLog.objects.all()[:50]
    return render(request, 'ariba_soc/sync_logs.html', {'logs': logs})
