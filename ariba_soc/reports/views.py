import csv
import io
from datetime import timedelta
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from alerts.models import Alert
from settings_manager.models import ReportSetting
from reports.services import generate_report

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
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    context = {
        'daily': {
            'total': Alert.objects.filter(alert_time__gte=today).count(),
            'open': Alert.objects.filter(status__in=['New', 'In Progress'], alert_time__gte=today).count(),
            'closed': Alert.objects.filter(status='Closed', alert_time__gte=today).count(),
            'critical': Alert.objects.filter(severity='Critical', alert_time__gte=today).count(),
            'true_positives': Alert.objects.filter(verdict='True Positive', alert_time__gte=today).count(),
            'false_positives': Alert.objects.filter(verdict='False Positive', alert_time__gte=today).count(),
        },
        'weekly_total': Alert.objects.filter(alert_time__gte=week_ago).count(),
        'monthly_total': Alert.objects.filter(alert_time__gte=month_ago).count(),
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
    relative_path = generate_report(report, errors=errors)
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
