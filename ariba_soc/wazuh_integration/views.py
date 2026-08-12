from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from .models import WazuhSyncLog, WazuhConfiguration, WazuhManagerConfig
from .forms import WazuhConfigurationForm, WazuhManagerConfigForm
from .services import ManagerClient, IndexerClient
from accounts.models import WAZUH_ALLOWED_ROLES


ALLOWED_ROLES = WAZUH_ALLOWED_ROLES

# Editing the Wazuh API URL/credentials changes where this app sends
# authenticated outbound requests -- an infrastructure-level change, not
# routine analyst work. Restricted tighter than viewing status/agents
# (ALLOWED_ROLES includes L1/L2) to prevent a low-privilege analyst
# redirecting those requests to an attacker-controlled host.
CONFIG_EDIT_ROLES = ['ADMIN', 'SOC_ENG', 'SOC_MGR']


def _check_wazuh_access(user):
    role = user.analyst_profile.role
    if role not in ALLOWED_ROLES:
        raise PermissionDenied("You do not have permission to access Wazuh integration.")


def _check_wazuh_config_edit_access(user):
    role = user.analyst_profile.role
    if role not in CONFIG_EDIT_ROLES:
        raise PermissionDenied("You do not have permission to edit Wazuh connection settings.")


@login_required
def wazuh_status(request):
    _check_wazuh_access(request.user)
    config = WazuhConfiguration.objects.first()
    manager_config = WazuhManagerConfig.objects.first()
    sync_logs = WazuhSyncLog.objects.all()[:20]

    form = WazuhConfigurationForm(instance=config) if config else WazuhConfigurationForm()
    manager_form = WazuhManagerConfigForm(instance=manager_config) if manager_config else WazuhManagerConfigForm()

    return render(request, 'ariba_soc/wazuh_status.html', {
        'config': config,
        'manager_config': manager_config,
        'sync_logs': sync_logs,
        'form': form,
        'manager_form': manager_form,
        'can_edit_wazuh_config': request.user.analyst_profile.role in CONFIG_EDIT_ROLES,
    })


@login_required
def wazuh_config_update(request):
    _check_wazuh_config_edit_access(request.user)
    if request.method == 'POST':
        config = WazuhConfiguration.objects.first()
        if config:
            form = WazuhConfigurationForm(request.POST, instance=config)
        else:
            form = WazuhConfigurationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Wazuh Indexer configuration updated.")
        else:
            messages.error(request, "Failed to update Indexer configuration.")
    return redirect('wazuh_integration:status')


@login_required
def wazuh_manager_config_update(request):
    _check_wazuh_config_edit_access(request.user)
    if request.method == 'POST':
        config = WazuhManagerConfig.objects.first()
        if config:
            form = WazuhManagerConfigForm(request.POST, instance=config)
        else:
            form = WazuhManagerConfigForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Wazuh Manager configuration updated.")
        else:
            messages.error(request, "Failed to update Manager configuration.")
    return redirect('wazuh_integration:status')


@login_required
def wazuh_agents(request):
    _check_wazuh_access(request.user)
    agents = []
    error = None
    try:
        manager_config = WazuhManagerConfig.objects.first()
        client = ManagerClient(manager_config)
        response = client.fetch_agents()
        agents = response.get('data', {}).get('affected_items', [])
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
    _check_wazuh_access(request.user)
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
    _check_wazuh_access(request.user)
    logs = WazuhSyncLog.objects.all()[:50]
    return render(request, 'ariba_soc/sync_logs.html', {'logs': logs})


@login_required
def test_manager_connection(request):
    _check_wazuh_access(request.user)
    try:
        manager_config = WazuhManagerConfig.objects.first()
        if not manager_config:
            return JsonResponse({'status': 'error', 'detail': 'Manager config not found.'}, status=400)
        client = ManagerClient(manager_config)
        token = client.authenticate()
        if token:
            return JsonResponse({'status': 'ok', 'api_url': client.base_url})
        return JsonResponse({'status': 'error', 'detail': 'Authentication failed'}, status=503)
    except Exception as e:
        return JsonResponse({'status': 'error', 'detail': str(e)}, status=503)


@login_required
def test_indexer_connection(request):
    _check_wazuh_access(request.user)
    try:
        config = WazuhConfiguration.objects.first()
        if not config:
            return JsonResponse({'status': 'error', 'detail': 'Indexer config not found.'}, status=400)
        client = IndexerClient(config)
        health = client.test_connection()
        return JsonResponse({'status': 'ok', 'cluster_health': health.get('status', 'unknown')})
    except Exception as e:
        return JsonResponse({'status': 'error', 'detail': str(e)}, status=503)


@login_required
def wazuh_health(request):
    """Health check endpoint for monitoring systems, load balancers, etc."""
    try:
        manager_config = WazuhManagerConfig.objects.first()
        if not manager_config:
            return JsonResponse({'status': 'error', 'detail': 'Manager configuration missing'}, status=503)
            
        client = ManagerClient(manager_config)
        token = client.authenticate()
        if token:
            return JsonResponse({'status': 'ok', 'api_url': client.base_url})
        return JsonResponse({'status': 'error', 'detail': 'Authentication failed'}, status=503)
    except Exception as e:
        return JsonResponse({'status': 'error', 'detail': str(e)}, status=503)
