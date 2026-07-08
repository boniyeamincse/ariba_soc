import csv
import io
from datetime import timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from alerts.models import Alert


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
    }
    return render(request, 'ariba_soc/reports_home.html', context)


@login_required
def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="ariba_alerts_export.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Time', 'Name', 'Severity', 'Status', 'Verdict', 'Assignee', 'Source', 'Host', 'Rule ID', 'Source IP', 'Username'])
    for alert in Alert.objects.all().select_related('assignee')[:5000]:
        writer.writerow([
            alert.id, alert.alert_time, alert.alert_name, alert.severity,
            alert.status, alert.verdict, alert.assignee, alert.source_name,
            alert.hostname, alert.rule_id, alert.source_ip, alert.username
        ])
    return response


@login_required
def export_excel(request):
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Alerts Export'
        headers = ['ID', 'Time', 'Name', 'Severity', 'Status', 'Verdict', 'Assignee', 'Source', 'Host', 'Rule ID']
        ws.append(headers)
        for alert in Alert.objects.all().select_related('assignee')[:5000]:
            ws.append([alert.id, str(alert.alert_time), alert.alert_name, alert.severity,
                       alert.status, alert.verdict, str(alert.assignee), alert.source_name,
                       alert.hostname, alert.rule_id])
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="ariba_alerts_export.xlsx"'
        return response
    except ImportError:
        return HttpResponse('openpyxl not installed. Install with: pip install openpyxl')
