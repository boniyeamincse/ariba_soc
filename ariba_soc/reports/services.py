import csv
import os
from datetime import timedelta
from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import Count
from django.utils import timezone
from alerts.models import Alert

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

REPORTS_DIR = os.path.join(settings.MEDIA_ROOT, 'reports')
PERIOD_DAYS = {'DAILY': 1, 'WEEKLY': 7, 'MONTHLY': 30, 'YEARLY': 365}


def is_due(report, now):
    if not report.last_generated_at:
        return True
    days = PERIOD_DAYS.get(report.schedule, 1)
    return (now - report.last_generated_at) > timedelta(days=days)


def _queryset(report, since):
    qs = Alert.objects.filter(alert_time__gte=since).select_related('assignee')
    if report.report_type == 'TP':
        qs = qs.filter(verdict='True Positive')
    elif report.report_type == 'FP':
        qs = qs.filter(verdict='False Positive')
    elif report.report_type == 'SLA':
        qs = qs.filter(sla_status='Breached')
    return qs


def _rows(report, qs):
    if report.report_type == 'ANALYST':
        headers = ['Analyst', 'Alerts Assigned']
        grouped = (qs.exclude(assignee__isnull=True)
                     .values('assignee__username')
                     .annotate(total=Count('id'))
                     .order_by('-total'))
        rows = [(g['assignee__username'], g['total']) for g in grouped]
    else:
        headers = ['Metric', 'Count']
        rows = [
            ('Total Alerts', qs.count()),
            ('Critical', qs.filter(severity='Critical').count()),
            ('High', qs.filter(severity='High').count()),
            ('Medium', qs.filter(severity='Medium').count()),
            ('Low', qs.filter(severity='Low').count()),
            ('Open', qs.filter(status__in=['New', 'In Progress']).count()),
            ('Closed', qs.filter(status='Closed').count()),
            ('True Positives', qs.filter(verdict='True Positive').count()),
            ('False Positives', qs.filter(verdict='False Positive').count()),
            ('SLA Breached', qs.filter(sla_status='Breached').count()),
        ]
    return headers, rows


def _write_csv(base, headers, rows):
    filepath = os.path.join(REPORTS_DIR, f'{base}.csv')
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    return filepath


def _write_excel(base, report, since, now, headers, rows):
    filepath = os.path.join(REPORTS_DIR, f'{base}.xlsx')
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = report.get_report_type_display()[:31]
    ws.append([report.name])
    ws.append([f'Period: {since.strftime("%Y-%m-%d")} to {now.strftime("%Y-%m-%d")}'])
    ws.append([])
    ws.append(headers)
    for row in rows:
        ws.append(list(row))
    wb.save(filepath)
    return filepath


def _write_pdf(base, report, since, now, headers, rows):
    filepath = os.path.join(REPORTS_DIR, f'{base}.pdf')
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(report.name, styles['Title']),
        Paragraph(report.get_report_type_display(), styles['Heading2']),
        Paragraph(
            f'Period: {since.strftime("%Y-%m-%d %H:%M")} &mdash; {now.strftime("%Y-%m-%d %H:%M")}',
            styles['Normal'],
        ),
        Spacer(1, 16),
    ]
    table_data = [headers] + [[str(c) for c in row] for row in rows]
    table = Table(table_data, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    doc.build(elements)
    return filepath


def email_report(report, filepath):
    email = EmailMessage(
        subject=f'SOC Report: {report.name}',
        body='Please find attached your scheduled SOC report.',
        to=[report.recipient_email],
    )
    email.attach_file(filepath)
    email.send(fail_silently=True)


def generate_report(report, now=None, errors=None):
    """Generate report's file for its current period, save it on the report,
    email it if a recipient is set, and return the relative media path
    (e.g. 'reports/x.pdf'), or None if generation failed."""
    now = now or timezone.now()
    os.makedirs(REPORTS_DIR, exist_ok=True)
    since = now - timedelta(days=PERIOD_DAYS.get(report.schedule, 1))
    qs = _queryset(report, since)
    headers, rows = _rows(report, qs)

    stamp = now.strftime('%Y%m%d-%H%M%S')
    safe_name = ''.join(c if c.isalnum() or c in '-_' else '_' for c in report.name) or 'report'
    base = f'{safe_name}_{stamp}'

    if report.export_format == 'CSV':
        filepath = _write_csv(base, headers, rows)
    elif report.export_format == 'EXCEL':
        if not HAS_OPENPYXL:
            if errors is not None:
                errors.append('openpyxl not installed, cannot generate EXCEL report')
            return None
        filepath = _write_excel(base, report, since, now, headers, rows)
    else:
        if not HAS_REPORTLAB:
            if errors is not None:
                errors.append('reportlab not installed, cannot generate PDF report')
            return None
        filepath = _write_pdf(base, report, since, now, headers, rows)

    relative_path = os.path.relpath(filepath, settings.MEDIA_ROOT)
    if report.recipient_email:
        email_report(report, filepath)
    report.last_generated_at = now
    report.last_report_file = relative_path
    report.save(update_fields=['last_generated_at', 'last_report_file'])
    return relative_path
