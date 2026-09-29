from django.utils import timezone
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.models import User
from settings_manager.models import NotificationSetting, AlarmSetting, AlarmSystemSetting, SystemSetting
from .models import Alert, AlertComment, AlertAuditLog, Notification

def create_audit_log(alert, user, action, old_value='', new_value='', request=None):
    ip = ''
    ua = ''
    if request:
        ip = request.META.get('REMOTE_ADDR', '')
        ua = request.META.get('HTTP_USER_AGENT', '')
    AlertAuditLog.objects.create(
        alert=alert,
        user=user,
        action=action,
        old_value=str(old_value),
        new_value=str(new_value),
        ip_address=ip,
        user_agent=ua,
    )


def update_alert(alert, form, user, request=None):
    changed = []
    for field in ['assignee', 'status', 'severity', 'verdict', 'priority']:
        old = str(getattr(alert, field) or '')
        new = str(form.cleaned_data.get(field) or '')
        if old != new:
            setattr(alert, field, form.cleaned_data[field])
            if field == 'status' and form.cleaned_data[field] == 'In Progress':
                alert.acknowledged_at = timezone.now()
            if field == 'status' and form.cleaned_data[field].startswith('Escalated'):
                alert.is_escalated = True
                alert.escalated_at = timezone.now()
                _notify_escalation(alert, f"{form.cleaned_data[field]} — {form.cleaned_data.get('escalation_reason', '')}")
            action_map = {
                'assignee': 'Assigned',
                'status': 'Status Changed',
                'severity': 'Severity Changed',
                'verdict': 'Verdict Changed',
                'priority': 'Priority Changed',
            }
            create_audit_log(alert, user, action_map.get(field, 'Updated'), old, new, request)
            changed.append(field)
            
            # Send notification if assignee changed and it's not the current user
            if field == 'assignee' and alert.assignee and alert.assignee != user:
                _notify_assignment(alert, alert.assignee, user, request)

    comment_text = form.cleaned_data.get('analyst_comment')
    if comment_text:
        AlertComment.objects.create(
            alert=alert,
            user=user,
            comment=comment_text,
            comment_type='Analyst Note'
        )
        alert.analyst_comment = comment_text
        create_audit_log(alert, user, 'Comment Added', '', comment_text[:200], request)

    escalation = form.cleaned_data.get('escalation_reason')
    if escalation:
        alert.escalation_reason = escalation
        AlertComment.objects.create(
            alert=alert,
            user=user,
            comment=f"Escalation reason: {escalation}",
            comment_type='Escalation Note'
        )

    remediation = form.cleaned_data.get('remediation_note')
    if remediation:
        alert.remediation_note = remediation
        AlertComment.objects.create(
            alert=alert,
            user=user,
            comment=f"Remediation: {remediation}",
            comment_type='Remediation Note'
        )

    closure = form.cleaned_data.get('closure_reason')
    if closure:
        alert.closure_reason = closure
        AlertComment.objects.create(
            alert=alert,
            user=user,
            comment=f"Closure reason: {closure}",
            comment_type='Closure Note'
        )

    lessons_learned = form.cleaned_data.get('lessons_learned')
    if lessons_learned:
        alert.root_cause_summary = lessons_learned
        AlertComment.objects.create(
            alert=alert,
            user=user,
            comment=f"Lessons learned: {lessons_learned}",
            comment_type='Lessons Learned'
        )

    if alert.status == 'Closed' and form.cleaned_data.get('verdict'):
        create_audit_log(alert, user, 'Closed', '', alert.verdict, request)

    alert.save()
    return changed


def _notify_assignment(alert, assignee, assigner, request=None):
    """Helper to send in-app notification and email to the assignee."""
    try:
        # Create In-App Notification
        link = reverse('alerts:detail', args=[alert.id])
        msg = f"Alert '{alert.alert_name}' was assigned to you by {assigner.username}."
        Notification.objects.create(user=assignee, message=msg, link=link)
        
        # Send Email
        if assignee.email:
            subject = f"[Ariba SOC] Alert Assigned: {alert.alert_name}"
            body = f"Hello {assignee.username},\n\nAn alert has been assigned to you by {assigner.username}.\n\nAlert: {alert.alert_name}\nSeverity: {alert.severity}\n\nPlease check your dashboard for details.\n\nThank you,\nAriba SOC"
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [assignee.email], fail_silently=True)
    except Exception as e:
        pass


def _notify_escalation(alert, reason=''):
    """Notify whoever Notification Settings says should hear about an
    escalation. Best-effort: a notification failure must never block the
    escalation itself."""
    try:
        settings_rows = NotificationSetting.objects.filter(event_type='ALERT_ESCALATED', is_active=True)
        if not settings_rows.exists():
            return
        link = reverse('alerts:detail', args=[alert.id])
        msg = f"Alert '{alert.alert_name}' was escalated." + (f" Reason: {reason}" if reason else '')

        recipients = set()
        for setting in settings_rows:
            if setting.recipient_user_id:
                recipients.add(setting.recipient_user)
            elif setting.recipient_role:
                for u in User.objects.filter(is_active=True, analyst_profile__role=setting.recipient_role):
                    recipients.add(u)

        for user in recipients:
            Notification.objects.create(user=user, message=msg, link=link)
            if user.email:
                send_mail(
                    f'[Ariba SOC] Alert Escalated: {alert.alert_name}',
                    f'{msg}\n\nSeverity: {alert.severity}\n\nPlease check your dashboard for details.',
                    settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True,
                )
    except Exception:
        pass


def _get_alarm_recipients():
    stored_roles = SystemSetting.get_setting('settings_allowed_roles', '')
    if stored_roles:
        roles = [r.strip() for r in stored_roles.split(',') if r.strip()]
    else:
        roles = ['SOC_MGR', 'SOC_ENG', 'ADMIN']
    return User.objects.filter(is_active=True, analyst_profile__role__in=roles).distinct()


def emit_alarm_notification(alert):
    """Create dashboard notifications for alerts when the severity is enabled."""
    try:
        if not AlarmSetting.severity_enabled(alert.severity):
            return 0

        AlarmSystemSetting.activate_for_alert(alert, f'Alarm triggered for {alert.alert_name}')
        recipients = list(_get_alarm_recipients())
        if not recipients:
            return 0

        link = reverse('alerts:detail', args=[alert.id])
        message = f"Alarm triggered: {alert.alert_name} [{alert.severity}]"
        created = 0
        for user in recipients:
            Notification.objects.create(user=user, message=message, link=link)
            created += 1
        return created
    except Exception:
        return 0


def assign_alert(alert, user, assignee=None, request=None):
    if assignee is None:
        assignee = user
    old = str(alert.assignee)
    
    notify = False
    if alert.assignee != assignee and assignee != user:
        notify = True
        
    alert.assignee = assignee
    alert.assigned_by = user
    alert.assigned_at = timezone.now()
    if alert.status == 'New':
        alert.status = 'In Progress'
        alert.acknowledged_at = timezone.now()
    alert.save()
    create_audit_log(alert, user, 'Assigned', old, str(assignee), request)
    
    if notify:
        _notify_assignment(alert, assignee, user, request)


def ingest_or_aggregate_alert(data):
    """
    Ingests a new alert or dynamically aggregates into an existing matching alert
    based on AlertAggregationSetting rules and AlertSuppressionRule exceptions.
    Returns: (alert or None, created: bool)
    """
    from datetime import timedelta
    from settings_manager.models import AlertAggregationSetting, AlertSuppressionRule

    # 1. Evaluate Alert Suppression Rules (False Positive / Noise Reduction)
    active_suppression_rules = AlertSuppressionRule.objects.filter(is_active=True)
    for srule in active_suppression_rules:
        if srule.matches(data):
            srule.match_count += 1
            srule.save(update_fields=['match_count'])
            if srule.action == 'DROP':
                return None, False
            elif srule.action == 'AUTO_CLOSE':
                data['status'] = 'Closed'
                data['verdict'] = 'False Positive'
                data['closure_reason'] = f'Auto-suppressed by rule: {srule.name}'
                if srule.reason:
                    data['root_cause_summary'] = f'Suppression justification: {srule.reason}'
            break

    agg_setting = AlertAggregationSetting.load()
    rule_id = str(data.get('rule_id', ''))
    source_ip = str(data.get('source_ip', ''))
    destination_ip = str(data.get('destination_ip', ''))
    agent_id = str(data.get('agent_id', ''))
    hostname = str(data.get('hostname', ''))
    username = str(data.get('username', ''))
    incoming_time = data.get('alert_time') or timezone.now()

    agg_key = agg_setting.generate_aggregation_key(
        rule_id=rule_id,
        source_ip=source_ip,
        destination_ip=destination_ip,
        agent_id=agent_id,
        hostname=hostname,
        username=username,
    ) if agg_setting.is_enabled else ''

    if agg_key:
        cutoff = incoming_time - timedelta(minutes=agg_setting.window_minutes)
        future_limit = incoming_time + timedelta(minutes=agg_setting.window_minutes)
        existing = Alert.objects.filter(
            aggregation_key=agg_key,
            status__in=['New', 'In Progress', 'Awaiting Action'],
            last_seen_at__gte=cutoff,
            last_seen_at__lte=future_limit,
            event_count__lt=agg_setting.max_events_per_alert,
        ).order_by('-last_seen_at').first()

        if existing:
            existing.event_count += 1
            if incoming_time > existing.last_seen_at:
                existing.last_seen_at = incoming_time
            if incoming_time < existing.first_seen_at:
                existing.first_seen_at = incoming_time
            existing.save(update_fields=['event_count', 'first_seen_at', 'last_seen_at', 'updated_at'])
            return existing, False

    data['aggregation_key'] = agg_key
    data['event_count'] = 1
    data['first_seen_at'] = incoming_time
    data['last_seen_at'] = incoming_time

    # Resolve asset & apply dynamic criticality multiplier
    asset = resolve_asset_for_alert(
        agent_id=agent_id,
        agent_ip=data.get('agent_ip'),
        hostname=hostname,
        destination_ip=destination_ip,
        source_ip=source_ip,
    )
    if asset:
        data['asset'] = asset
        data['asset_criticality'] = asset.criticality
        multiplier = float(asset.criticality_multiplier or 1.0)
        base_map = {'Critical': 90, 'High': 70, 'Medium': 50, 'Low': 25, 'Informational': 10}
        score = data.get('severity_score') or base_map.get(data.get('severity', 'Medium'), 50)
        data['risk_score'] = round(min(100.0, score * multiplier), 1)

        if asset.criticality == 'CRITICAL':
            data['priority'] = 'Critical'
            data['is_incident_candidate'] = True
            if data.get('severity') in ['Informational', 'Low', 'Medium']:
                data['severity'] = 'High'
        elif asset.criticality == 'HIGH':
            if data.get('priority') in ['Low', 'Medium', None]:
                data['priority'] = 'High'
            if data.get('severity') in ['Informational', 'Low']:
                data['severity'] = 'Medium'
    else:
        base_map = {'Critical': 90, 'High': 70, 'Medium': 50, 'Low': 25, 'Informational': 10}
        data['risk_score'] = float(data.get('severity_score') or base_map.get(data.get('severity', 'Medium'), 50))

    alert = Alert.objects.create(**data)
    return alert, True


# ---------------------------------------------------------------------------
# Phase 5: Asset Inventory & Criticality Multiplier Service
# ---------------------------------------------------------------------------

def resolve_asset_for_alert(agent_id=None, agent_ip=None, hostname=None, source_ip=None, destination_ip=None):
    """
    Attempts to match an active Asset in the inventory based on agent_id,
    hostname, agent_ip, destination_ip, or source_ip.
    """
    from alerts.models import Asset

    # 1. Match by agent_id (most reliable for endpoint telemetry)
    if agent_id and str(agent_id).strip():
        asset = Asset.objects.filter(agent_id=str(agent_id).strip(), is_active=True).first()
        if asset:
            return asset

    # 2. Match by hostname
    if hostname and str(hostname).strip():
        h = str(hostname).strip()
        asset = Asset.objects.filter(hostname__iexact=h, is_active=True).first()
        if asset:
            return asset

    # 3. Match by agent IP
    if agent_ip and str(agent_ip).strip():
        asset = Asset.objects.filter(ip_address=str(agent_ip).strip(), is_active=True).first()
        if asset:
            return asset

    # 4. Match by destination IP (target server in network alerts)
    if destination_ip and str(destination_ip).strip():
        asset = Asset.objects.filter(ip_address=str(destination_ip).strip(), is_active=True).first()
        if asset:
            return asset

    # 5. Match by source IP (in case the compromised machine is initiating)
    if source_ip and str(source_ip).strip():
        asset = Asset.objects.filter(ip_address=str(source_ip).strip(), is_active=True).first()
        if asset:
            return asset

    return None


def apply_asset_criticality(alert, asset=None):
    """
    Calculates dynamic risk score and adjusts alert priority & severity based
    on the business asset's criticality multiplier.
    """
    if asset is None:
        asset = resolve_asset_for_alert(
            agent_id=getattr(alert, 'agent_id', None),
            agent_ip=getattr(alert, 'agent_ip', None),
            hostname=getattr(alert, 'hostname', None),
            destination_ip=getattr(alert, 'destination_ip', None),
            source_ip=getattr(alert, 'source_ip', None),
        )

    if asset:
        alert.asset = asset
        alert.asset_criticality = asset.criticality
        multiplier = float(asset.criticality_multiplier or 1.0)

        # Baseline score from rule level or severity
        base_map = {'Critical': 90, 'High': 70, 'Medium': 50, 'Low': 25, 'Informational': 10}
        score = alert.severity_score if alert.severity_score > 0 else base_map.get(alert.severity, 50)
        
        # Dynamic risk score capped at 100
        alert.risk_score = round(min(100.0, score * multiplier), 1)

        # Dynamic priority and severity adjustment for high-value targets
        if asset.criticality == 'CRITICAL':
            alert.priority = 'Critical'
            alert.is_incident_candidate = True
            if alert.severity in ['Informational', 'Low', 'Medium']:
                alert.severity = 'High'
        elif asset.criticality == 'HIGH':
            if alert.priority in ['Low', 'Medium']:
                alert.priority = 'High'
            if alert.severity in ['Informational', 'Low']:
                alert.severity = 'Medium'
        elif asset.criticality == 'LOW':
            if alert.priority == 'Critical' and alert.severity not in ['Critical']:
                alert.priority = 'Medium'
    else:
        base_map = {'Critical': 90, 'High': 70, 'Medium': 50, 'Low': 25, 'Informational': 10}
        alert.risk_score = float(alert.severity_score if alert.severity_score > 0 else base_map.get(alert.severity, 50))

    return alert


def sync_assets_from_wazuh():
    """
    Queries Wazuh Manager API for registered/connected agents and auto-populates
    or updates the Asset Directory.
    Returns: dict with 'created', 'updated', 'total'
    """
    from wazuh_integration.models import WazuhManagerConfig
    from wazuh_integration.services import ManagerClient
    from alerts.models import Asset

    manager_config = WazuhManagerConfig.objects.first()
    if not manager_config:
        return {'created': 0, 'updated': 0, 'total': 0, 'error': 'No Wazuh Manager configured'}

    client = ManagerClient(manager_config)
    response = client.fetch_agents()
    items = response.get('data', {}).get('affected_items', [])
    if not items and 'data' in response and 'items' in response['data']:
        items = response['data']['items']

    created_count = 0
    updated_count = 0

    for item in items:
        agent_id = str(item.get('id', '')).strip()
        hostname = str(item.get('name', '')).strip()
        ip_addr = item.get('ip')
        if ip_addr in ['any', '127.0.0.1', None]:
            ip_addr = None

        os_data = item.get('os', {})
        os_str = f"{os_data.get('name', '')} {os_data.get('version', '')}".strip()

        # Check existing
        asset = Asset.objects.filter(agent_id=agent_id).first()
        if not asset and hostname:
            asset = Asset.objects.filter(hostname__iexact=hostname).first()

        now = timezone.now()

        if asset:
            updated = False
            if ip_addr and asset.ip_address != ip_addr:
                asset.ip_address = ip_addr
                updated = True
            if os_str and asset.os_name != os_str:
                asset.os_name = os_str
                updated = True
            if not asset.agent_id and agent_id:
                asset.agent_id = agent_id
                updated = True
            asset.last_seen_at = now
            asset.save()
            updated_count += 1
        else:
            asset_type = 'SERVER'
            criticality = 'MEDIUM'
            name_lower = hostname.lower()
            if any(k in name_lower for k in ['dc', 'domain', 'ad']):
                asset_type = 'DOMAIN_CONTROLLER'
                criticality = 'CRITICAL'
            elif any(k in name_lower for k in ['db', 'sql', 'postgres', 'mongo', 'oracle']):
                asset_type = 'DATABASE'
                criticality = 'HIGH'
            elif any(k in name_lower for k in ['pay', 'bank', 'swift', 'core']):
                asset_type = 'PAYMENT_GATEWAY'
                criticality = 'CRITICAL'
            elif 'manager' in name_lower or agent_id == '000':
                asset_type = 'SERVER'
                criticality = 'HIGH'

            Asset.objects.create(
                hostname=hostname or f"agent-{agent_id}",
                name=hostname or f"Agent {agent_id}",
                agent_id=agent_id,
                ip_address=ip_addr,
                os_name=os_str,
                asset_type=asset_type,
                criticality=criticality,
                environment='PROD',
                auto_discovered=True,
                last_seen_at=now,
            )
            created_count += 1

    return {
        'created': created_count,
        'updated': updated_count,
        'total': len(items),
    }


def recalculate_alerts_risk_score():
    """
    Batch recalculates dynamic risk score and asset links for existing alerts.
    """
    count = 0
    for alert in Alert.objects.select_related('asset').all():
        apply_asset_criticality(alert)
        alert.save(update_fields=['asset', 'asset_criticality', 'risk_score', 'priority', 'severity', 'is_incident_candidate'])
        count += 1
    return count



