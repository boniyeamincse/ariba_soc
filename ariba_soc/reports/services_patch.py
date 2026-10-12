import os
from datetime import datetime
from django.conf import settings
from django.template.loader import render_to_string
from alerts.models import Alert
from .models import ReportSetting

try:
    from xhtml2pdf import pisa
except ImportError:
    pisa = None

def _write_pdf_xhtml(base, report, since, now, headers, rows, generated_by=None):
    from reports.services import REPORTS_DIR, _generated_by_label
    
    filepath = os.path.join(REPORTS_DIR, f'{base}.pdf')
    
    # Query Data
    qs = Alert.objects.filter(alert_time__gte=since, alert_time__lte=now)
    
    total_alerts = qs.count()
    critical = qs.filter(severity='Critical').count()
    high = qs.filter(severity='High').count()
    medium = qs.filter(severity='Medium').count()
    low = qs.filter(severity='Low').count()
    
    # Top assets manually counted (assuming PostgreSQL or just raw for simplicity)
    # This is a bit complex in ORM without proper group by. We'll approximate.
    from django.db.models import Count, Max
    top_assets = qs.values('hostname').annotate(
        count=Count('id'),
    ).order_by('-count')[:5]
    
    for a in top_assets:
        # Determine highest severity for this asset
        sev_order = {'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1, 'Informational': 0}
        sevs = set(qs.filter(hostname=a['hostname']).values_list('severity', flat=True))
        highest = max(sevs, key=lambda s: sev_order.get(s, -1)) if sevs else 'None'
        a['highest'] = highest

    mitre_tactics = qs.exclude(rule_description='').values('rule_description').annotate(count=Count('id')).order_by('-count')[:5]
    for t in mitre_tactics:
        t['tactic'] = t['rule_description'][:30] # approximation since mitre field missing

    recent_critical = qs.filter(severity__in=['Critical', 'High']).order_by('-alert_time')[:10]

    context = {
        'report': report,
        'since': since,
        'now': now,
        'generated_by': _generated_by_label(generated_by),
        'total_alerts': total_alerts,
        'critical_alerts': critical,
        'high_alerts': high,
        'medium_alerts': medium,
        'low_alerts': low,
        'top_assets': top_assets,
        'mitre_tactics': mitre_tactics,
        'recent_critical': recent_critical,
    }
    
    html_string = render_to_string('reports/pdf/executive_summary.html', context)
    
    with open(filepath, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(
            html_string, dest=pdf_file
        )
    
    return filepath

