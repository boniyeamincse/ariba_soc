import csv
import io
from datetime import datetime, timedelta
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from alerts.models import Alert
from settings_manager.models import ReportSetting
from reports.services import generate_report, calculate_soc_manager_daily_report

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


def _apply_export_filters(request):
    alerts = Alert.objects.select_related('assignee').all()
    severity = request.GET.get('severity')
    status = request.GET.get('status')
    verdict = request.GET.get('verdict')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if severity:
        alerts = alerts.filter(severity=severity)
    if status:
        alerts = alerts.filter(status=status)
    if verdict:
        alerts = alerts.filter(verdict=verdict)
    if date_from:
        alerts = alerts.filter(alert_time__gte=date_from)
    if date_to:
        alerts = alerts.filter(alert_time__lte=date_to)
    total = alerts.count()
    if total > 5000:
        alerts = alerts[:5000]
    return alerts, total


@login_required
def reports_home(request):
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    range_param = request.GET.get('range', '').strip()
    custom_from = request.GET.get('date_from', '').strip()
    custom_to = request.GET.get('date_to', '').strip()

    # Intelligent default: if no range requested, use 'today' if alerts exist today,
    # otherwise fallback to 'all' or '30d' so SOC Managers see their full alert telemetry!
    if not range_param:
        if Alert.objects.filter(alert_time__gte=today_start).exists():
            range_param = 'today'
        elif Alert.objects.filter(alert_time__gte=today_start - timedelta(days=7)).exists():
            range_param = '7d'
        elif Alert.objects.filter(alert_time__gte=today_start - timedelta(days=30)).exists():
            range_param = '30d'
        else:
            range_param = 'all'

    date_from = None
    date_to = None

    if range_param == 'today':
        date_from = today_start
        date_to = now
    elif range_param == 'yesterday':
        yesterday_start = today_start - timedelta(days=1)
        date_from = yesterday_start
        date_to = today_start - timedelta(microseconds=1)
    elif range_param == '7d':
        date_from = now - timedelta(days=7)
        date_to = now
    elif range_param == '30d':
        date_from = now - timedelta(days=30)
        date_to = now
    elif range_param == 'all':
        date_from = None
        date_to = None
    elif range_param == 'custom':
        if custom_from:
            try:
                date_from = timezone.make_aware(datetime.strptime(custom_from, '%Y-%m-%d'))
            except (ValueError, TypeError):
                pass
        if custom_to:
            try:
                parsed_to = datetime.strptime(custom_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                date_to = timezone.make_aware(parsed_to)
            except (ValueError, TypeError):
                pass

    report = calculate_soc_manager_daily_report(date_from=date_from, date_to=date_to)

    daily_compat = {
        'total': report['total_alerts'],
        'open': report['open_cases'],
        'closed': report['closed_cases'],
        'critical': report['critical'],
        'true_positives': report['true_positives'],
        'false_positives': report['false_positives'],
    }

    context = {
        'report': report,
        'daily': daily_compat,
        'selected_range': range_param,
        'custom_from': custom_from,
        'custom_to': custom_to,
        'date_from': date_from,
        'date_to': date_to,
        'HAS_OPENPYXL': HAS_OPENPYXL,
        'report_settings': ReportSetting.objects.order_by('name'),
        'MEDIA_URL': settings.MEDIA_URL,
    }
    return render(request, 'ariba_soc/reports_home.html', context)


@login_required
@require_POST
def generate_now(request, pk):
    report = get_object_or_404(ReportSetting, pk=pk)
    errors = []
    relative_path = generate_report(report, errors=errors, generated_by=request.user)
    if relative_path:
        messages.success(request, f'Generated "{report.name}".')
    else:
        messages.error(request, f'Failed to generate "{report.name}": ' + '; '.join(errors or ['unknown error']))
    return redirect('reports:home')


@login_required
def export_csv(request):
    alerts, total = _apply_export_filters(request)
    if total > 5000:
        messages.warning(request, f'Export limited to 5000 of {total} alerts. Apply date filters to narrow results.')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="ariba_alerts_export.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Time', 'Name', 'Severity', 'Status', 'Verdict', 'Assignee', 'Source', 'Host', 'Rule ID', 'Source IP', 'Username'])
    for alert in alerts.only('id', 'alert_time', 'alert_name', 'severity', 'status', 'verdict', 'assignee', 'source_name', 'hostname', 'rule_id', 'source_ip', 'username'):
        writer.writerow([
            alert.id, alert.alert_time, alert.alert_name, alert.severity,
            alert.status, alert.verdict, alert.assignee, alert.source_name,
            alert.hostname, alert.rule_id, alert.source_ip, alert.username
        ])
    return response


@login_required
def export_excel(request):
    if not HAS_OPENPYXL:
        return HttpResponse('openpyxl not installed. Install with: pip install openpyxl', status=501)
    alerts, total = _apply_export_filters(request)
    if total > 5000:
        messages.warning(request, f'Export limited to 5000 of {total} alerts. Apply date filters to narrow results.')
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Alerts Export'
    headers = ['ID', 'Time', 'Name', 'Severity', 'Status', 'Verdict', 'Assignee', 'Source', 'Host', 'Rule ID']
    ws.append(headers)
    for alert in alerts.only('id', 'alert_time', 'alert_name', 'severity', 'status', 'verdict', 'assignee', 'source_name', 'hostname', 'rule_id'):
        ws.append([alert.id, str(alert.alert_time), alert.alert_name, alert.severity,
                   alert.status, alert.verdict, str(alert.assignee), alert.source_name,
                   alert.hostname, alert.rule_id])
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="ariba_alerts_export.xlsx"'
    return response


# ---------------------------------------------------------------------------
# MTTA / MTTR Analytics Views (Phase 4)
# ---------------------------------------------------------------------------
from datetime import datetime
from django.contrib.auth.models import User
from reports.services import calculate_mtta_mttr_analytics


def _parse_mtta_filters(request):
    range_param = request.GET.get('range', '30d')
    severity = request.GET.get('severity', 'All')
    assignee = request.GET.get('assignee', 'All')
    custom_from = request.GET.get('date_from', '').strip()
    custom_to = request.GET.get('date_to', '').strip()

    now = timezone.now()
    date_from = None
    date_to = None

    if range_param == '24h':
        date_from = now - timedelta(hours=24)
        date_to = now
    elif range_param == '7d':
        date_from = now - timedelta(days=7)
        date_to = now
    elif range_param == '30d':
        date_from = now - timedelta(days=30)
        date_to = now
    elif range_param == '90d':
        date_from = now - timedelta(days=90)
        date_to = now
    elif range_param == 'all':
        date_from = None
        date_to = None
    elif range_param == 'custom':
        if custom_from:
            try:
                date_from = timezone.make_aware(datetime.strptime(custom_from, '%Y-%m-%d'))
            except (ValueError, TypeError):
                pass
        if custom_to:
            try:
                parsed_to = datetime.strptime(custom_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                date_to = timezone.make_aware(parsed_to)
            except (ValueError, TypeError):
                pass

    return {
        'range': range_param,
        'severity': severity,
        'assignee': assignee,
        'date_from': date_from,
        'date_to': date_to,
        'custom_from': custom_from,
        'custom_to': custom_to,
    }


@login_required
def mtta_mttr_analytics(request):
    filters = _parse_mtta_filters(request)
    metrics = calculate_mtta_mttr_analytics(
        date_from=filters['date_from'],
        date_to=filters['date_to'],
        severity=filters['severity'],
        assignee_id=filters['assignee'],
    )
    analysts = User.objects.filter(is_active=True).select_related('analyst_profile').order_by('username')
    context = {
        'metrics': metrics,
        'selected_range': filters['range'],
        'selected_severity': filters['severity'],
        'selected_assignee': filters['assignee'],
        'custom_from': filters['custom_from'],
        'custom_to': filters['custom_to'],
        'analysts': analysts,
        'severities': ['Critical', 'High', 'Medium', 'Low', 'Informational'],
    }
    return render(request, 'ariba_soc/mtta_mttr_analytics.html', context)


@login_required
def export_mtta_mttr_csv(request):
    filters = _parse_mtta_filters(request)
    metrics = calculate_mtta_mttr_analytics(
        date_from=filters['date_from'],
        date_to=filters['date_to'],
        severity=filters['severity'],
        assignee_id=filters['assignee'],
    )
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="ariba_mtta_mttr_sla_analytics.csv"'
    writer = csv.writer(response)

    writer.writerow(['ARIBA SOC — MTTA / MTTR & SLA PERFORMANCE REPORT'])
    writer.writerow(['Generated on', timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')])
    writer.writerow(['Range Filter', filters['range']])
    writer.writerow(['Severity Filter', filters['severity']])
    writer.writerow(['Assignee Filter', filters['assignee']])
    writer.writerow([])

    writer.writerow(['--- EXECUTIVE METRICS ---'])
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Total Alerts', metrics['total_alerts']])
    writer.writerow(['Total Acknowledged', metrics['total_acknowledged']])
    writer.writerow(['Total Resolved', metrics['total_resolved']])
    writer.writerow(['Avg MTTA (Mean Time to Acknowledge)', metrics['avg_mtta_display']])
    writer.writerow(['Median MTTA', metrics['median_mtta_display']])
    writer.writerow(['Avg MTTR (Mean Time to Resolve)', metrics['avg_mttr_display']])
    writer.writerow(['Median MTTR', metrics['median_mttr_display']])
    writer.writerow(['SLA Compliance Rate', f"{metrics['sla_compliance_rate']}%"])
    writer.writerow(['Total SLA Breaches', metrics['total_breached']])
    writer.writerow([])

    writer.writerow(['--- SEVERITY PERFORMANCE BREAKDOWN ---'])
    writer.writerow(['Severity', 'Total Alerts', 'Avg MTTA', 'Median MTTA', 'Target Ack', 'Ack SLA %', 'Avg MTTR', 'Median MTTR', 'Target Resolve', 'Resolve SLA %', 'Breaches', 'Overall SLA Compliance %'])
    for s in metrics['severity_breakdown']:
        writer.writerow([
            s['severity'], s['total'], s['avg_mtta_display'], s['median_mtta_display'],
            s['ack_target_display'], f"{s['ack_compliance_pct']}%",
            s['avg_mttr_display'], s['median_mttr_display'],
            s['res_target_display'], f"{s['res_compliance_pct']}%",
            s['breached'], f"{s['sla_compliance_pct']}%",
        ])
    writer.writerow([])

    writer.writerow(['--- ANALYST PERFORMANCE LEADERBOARD ---'])
    writer.writerow(['Analyst', 'Role', 'Assigned', 'In Progress', 'Resolved', 'Avg MTTA', 'Median MTTA', 'Avg MTTR', 'Median MTTR', 'Breaches', 'SLA Adherence %', 'TP Rate %'])
    for a in metrics['analysts_breakdown']:
        writer.writerow([
            a['full_name'] or a['username'], a['role'], a['assigned'],
            a['in_progress'], a['resolved'], a['avg_mtta_display'],
            a['median_mtta_display'], a['avg_mttr_display'],
            a['median_mttr_display'], a['breached'],
            f"{a['sla_adherence_pct']}%", f"{a['tp_rate']}%",
        ])

    return response

