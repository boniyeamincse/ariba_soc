from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
import logging
from .models import WazuhSyncLog, WazuhConfiguration, WazuhManagerConfig, ActiveResponseExecution
from .forms import WazuhConfigurationForm, WazuhManagerConfigForm
from .services import ManagerClient, IndexerClient
from accounts.models import WAZUH_ALLOWED_ROLES
from alerts.models import Alert, AlertComment, AlertAuditLog

logger = logging.getLogger(__name__)

ALLOWED_ROLES = WAZUH_ALLOWED_ROLES
CONFIG_EDIT_ROLES = ['ADMIN', 'SOC_ENG', 'SOC_MGR']
CONTAINMENT_ROLES = ['ADMIN', 'SOC_ENG', 'SOC_MGR', 'L2', 'L3']


def _check_wazuh_access(user):
    if user.is_superuser:
        return True
    if not hasattr(user, 'analyst_profile') or not user.analyst_profile:
        raise PermissionDenied("User profile required.")
    role = user.analyst_profile.role
    if role not in ALLOWED_ROLES:
        raise PermissionDenied("You do not have permission to access Wazuh integration.")


def _check_containment_access(user):
    if user.is_superuser:
        return True
    if hasattr(user, 'analyst_profile') and user.analyst_profile:
        if user.analyst_profile.role in CONTAINMENT_ROLES:
            return True
    raise PermissionDenied("You do not have permission to execute SOAR containment active responses.")



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


@login_required
@require_POST
def active_response_execute(request):
    _check_containment_access(request.user)

    command = request.POST.get('command')
    agent_id = request.POST.get('agent_id')
    target_ip = request.POST.get('target_ip', '').strip()
    target_user = request.POST.get('target_user', '').strip()
    alert_id = request.POST.get('alert_id')
    next_url = request.POST.get('next')

    alert = Alert.objects.filter(id=alert_id).first() if alert_id else None

    if not command:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Missing active response command.'}, status=400)
        messages.error(request, 'Missing active response command.')
        return redirect(next_url or 'alerts:table')

    if not agent_id:
        if alert and alert.agent_id:
            agent_id = alert.agent_id
        else:
            agent_id = '001'

    arguments = []
    if command in ['firewall-drop', 'host-deny']:
        if not target_ip and alert:
            target_ip = alert.source_ip
        if not target_ip:
            msg = 'A target IP address is required for firewall-drop / host-deny.'
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect(next_url or 'alerts:table')
        arguments = ['-', target_ip]
    elif command == 'disable-account':
        if not target_user and alert:
            target_user = alert.username
        if not target_user:
            msg = 'A target username is required for disable-account.'
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect(next_url or 'alerts:table')
        arguments = ['-', target_user]

    try:
        manager_config = WazuhManagerConfig.objects.first()
        client = ManagerClient(manager_config)
        res = client.execute_active_response(command=command, agent_id=agent_id, arguments=arguments)

        status_val = 'SUCCESS' if res['success'] else 'FAILED'
        exec_record = ActiveResponseExecution.objects.create(
            alert=alert,
            user=request.user,
            command=command,
            target_agent_id=str(agent_id),
            target_agent_name=alert.agent_name if alert else '',
            target_ip=target_ip,
            target_user=target_user,
            status=status_val,
            response_message=res['message'],
            response_json=res.get('raw', {}),
        )

        if alert:
            action_desc = f"Executed Active Response: {command} on agent {agent_id}"
            if target_ip:
                action_desc += f" (Target IP: {target_ip})"
            if target_user:
                action_desc += f" (Target User: {target_user})"

            AlertComment.objects.create(
                alert=alert,
                user=request.user,
                comment=f"⚡ SOAR Active Response: {action_desc} -> Result: {status_val} ({res['message']})",
                comment_type='Investigation Note'
            )
            AlertAuditLog.objects.create(
                alert=alert,
                user=request.user,
                action='SOAR Containment',
                old_value='',
                new_value=f"{command}: {status_val}"
            )

        if res['success']:
            msg = f"Containment executed: {res['message']}"
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'ok', 'message': msg, 'execution_id': exec_record.id})
            messages.success(request, msg)
        else:
            msg = f"Containment request processed: {res['message']}"
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'warning', 'message': msg, 'execution_id': exec_record.id})
            messages.warning(request, msg)

    except Exception as e:
        logger.error(f"Failed to execute containment: {e}")
        msg = f"Failed to execute containment: {str(e)}"
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': msg}, status=500)
        messages.error(request, msg)

    if next_url:
        return redirect(next_url)
    return redirect('alerts:detail', alert.id) if alert else redirect('wazuh_integration:active_response_history')


@login_required
def active_response_history(request):
    _check_wazuh_access(request.user)
    executions = ActiveResponseExecution.objects.select_related('alert', 'user').all()[:100]
    can_contain = request.user.is_superuser or (hasattr(request.user, 'analyst_profile') and request.user.analyst_profile.role in CONTAINMENT_ROLES)
    return render(request, 'ariba_soc/active_response_history.html', {
        'executions': executions,
        'can_contain': can_contain,
    })

