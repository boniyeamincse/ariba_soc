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
from reports.services import generate_report, _pdf_header_footer, BRAND_NAVY, BRAND_BLUE, BRAND_ACCENT, BRAND_DARK, BRAND_GRAY, BRAND_LIGHTGRAY, BRAND_BORDER, BRAND_BG_LIGHT, COMPANY_NAME, TEAM_NAME, REPORT_TAGLINE

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


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


@login_required
def export_pdf(request):
    if not HAS_REPORTLAB:
        return HttpResponse('reportlab not installed. Install with: pip install reportlab', status=501)

    alerts, total = _apply_export_filters(request)
    now = timezone.now()
    generated_by_label = request.user.get_full_name() or request.user.username
    profile = getattr(request.user, 'analyst_profile', None)
    if profile:
        generated_by_label += f' ({profile.get_role_display()})'

    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output, pagesize=landscape(A4),
        topMargin=34 * mm, bottomMargin=24 * mm,
        leftMargin=15 * mm, rightMargin=15 * mm,
    )
    styles = getSampleStyleSheet()

    severity = request.GET.get('severity', 'All')
    status = request.GET.get('status', 'All')
    verdict = request.GET.get('verdict', 'All')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    period_label = f'{date_from} to {date_to}' if date_from and date_to else 'All Time'
    if total > 5000:
        period_label += f' (limited to 5,000 of {total:,})'

    title_style = styles['Title']
    title_style.fontSize = 18
    title_style.textColor = colors.HexColor(BRAND_NAVY)
    title_style.spaceAfter = 2

    subtitle_style = styles['Normal']
    subtitle_style.fontSize = 9
    subtitle_style.textColor = colors.HexColor(BRAND_GRAY)
    subtitle_style.spaceAfter = 14

    elements = []

    # Title
    elements.append(Paragraph('Alert Export Report', title_style))
    elements.append(Paragraph(
        f'{COMPANY_NAME} | {TEAM_NAME} | {REPORT_TAGLINE}',
        subtitle_style
    ))

    # Summary cards
    critical_count = alerts.filter(severity='Critical').count() if total > 0 else 0
    high_count = alerts.filter(severity='High').count() if total > 0 else 0
    open_count = alerts.filter(status__in=['New', 'In Progress']).count() if total > 0 else 0

    summary_rows = [
        ['Total Alerts', 'Critical', 'High', 'Open'],
        [str(min(total, 5000)), str(critical_count), str(high_count), str(open_count)],
    ]
    summary_table = Table(summary_rows, colWidths=[45 * mm, 45 * mm, 45 * mm, 45 * mm], hAlign='LEFT')
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, 1), 14),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(BRAND_GRAY)),
        ('TEXTCOLOR', (0, 1), (0, 1), colors.HexColor(BRAND_ACCENT)),
        ('TEXTCOLOR', (1, 1), (1, 1), colors.HexColor('#dc2626')),
        ('TEXTCOLOR', (2, 1), (2, 1), colors.HexColor('#ea580c')),
        ('TEXTCOLOR', (3, 1), (3, 1), colors.HexColor(BRAND_NAVY)),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
        ('TOPPADDING', (0, 1), (-1, 1), 0),
        ('LINEBELOW', (0, 1), (-1, 1), 0.5, colors.HexColor(BRAND_BORDER)),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 12))

    # Meta info
    meta_rows = [
        ['Filters Applied', f'Severity: {severity}  |  Status: {status}  |  Verdict: {verdict}'],
        ['Period', period_label],
        ['Generated By', generated_by_label],
        ['Date & Time', now.strftime('%d %B %Y at %H:%M')],
    ]
    meta_table = Table(meta_rows, colWidths=[35 * mm, 120 * mm], hAlign='LEFT')
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor(BRAND_NAVY)),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor(BRAND_DARK)),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.HexColor(BRAND_BORDER)),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 14))

    # Data table
    headers = ['ID', 'Time', 'Name', 'Severity', 'Status', 'Verdict', 'Assignee', 'Source', 'Host', 'Rule ID', 'Source IP', 'User']
    field_names = ['id', 'alert_time', 'alert_name', 'severity', 'status', 'verdict', 'assignee', 'source_name', 'hostname', 'rule_id', 'source_ip', 'username']

    table_data = [headers]
    for alert in alerts.only(*field_names):
        assignee = str(alert.assignee) if alert.assignee else '-'
        time_str = alert.alert_time.strftime('%Y-%m-%d %H:%M') if alert.alert_time else '-'
        table_data.append([
            str(alert.id),
            time_str,
            (alert.alert_name or '-')[:50],
            alert.severity or '-',
            alert.status or '-',
            alert.verdict or '-',
            assignee,
            alert.source_name or '-',
            (alert.hostname or '-')[:25],
            alert.rule_id or '-',
            alert.source_ip or '-',
            (alert.username or '-')[:15],
        ])

    col_widths = [18*mm, 32*mm, 55*mm, 22*mm, 28*mm, 28*mm, 25*mm, 22*mm, 30*mm, 18*mm, 28*mm, 25*mm]
    table = Table(table_data, colWidths=col_widths, repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(BRAND_NAVY)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7.5),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor(BRAND_BORDER)),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor(BRAND_BG_LIGHT)]),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
    ]))
    elements.append(table)

    if total == 0:
        elements.append(Spacer(1, 12))
        no_data_style = styles['Normal']
        no_data_style.textColor = colors.HexColor(BRAND_GRAY)
        no_data_style.alignment = 1
        elements.append(Paragraph('No alerts match the selected filters.', no_data_style))

    draw = _pdf_header_footer(generated_by_label, now)
    doc.build(elements, onFirstPage=draw, onLaterPages=draw)

    output.seek(0)
    response = HttpResponse(output.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="AkijGroup_SOC_Report_{now.strftime("%Y%m%d_%H%M%S")}.pdf"'
    return response
