from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from vulnerabilities.models import VulnerabilityCase, STATUS_CHOICES, PRIORITY_CHOICES


def get_overview_metrics():
    total = VulnerabilityCase.objects.count()
    by_status = dict(VulnerabilityCase.objects.values_list('status').annotate(c=Count('id')).values_list('status', 'c'))
    by_priority = dict(VulnerabilityCase.objects.values_list('priority').annotate(c=Count('id')).values_list('priority', 'c'))

    now = timezone.now()
    overdue = VulnerabilityCase.objects.filter(
        due_at__lt=now
    ).exclude(status__in=['RESOLVED', 'RISK_ACCEPTED', 'FALSE_POSITIVE']).count()

    critical = VulnerabilityCase.objects.filter(priority='CRITICAL').exclude(
        status__in=['RESOLVED', 'RISK_ACCEPTED', 'FALSE_POSITIVE']
    ).count()

    high = VulnerabilityCase.objects.filter(priority='HIGH').exclude(
        status__in=['RESOLVED', 'RISK_ACCEPTED', 'FALSE_POSITIVE']
    ).count()

    risk_accepted = VulnerabilityCase.objects.filter(risk_accepted=True).count()

    last_7d = VulnerabilityCase.objects.filter(created_at__gte=now - timedelta(days=7)).count()
    last_30d = VulnerabilityCase.objects.filter(created_at__gte=now - timedelta(days=30)).count()

    return {
        'total': total,
        'by_status': by_status,
        'by_priority': by_priority,
        'overdue': overdue,
        'critical_open': critical,
        'high_open': high,
        'risk_accepted': risk_accepted,
        'new_last_7d': last_7d,
        'new_last_30d': last_30d,
    }


def get_inventory(filters=None, page=1, page_size=50):
    qs = VulnerabilityCase.objects.all()
    if filters:
        if filters.get('status'):
            qs = qs.filter(status=filters['status'])
        if filters.get('priority'):
            qs = qs.filter(priority=filters['priority'])
        if filters.get('cve_id'):
            qs = qs.filter(cve_id__icontains=filters['cve_id'])
        if filters.get('agent_id'):
            qs = qs.filter(agent_id=filters['agent_id'])
        if filters.get('owner'):
            qs = qs.filter(owner_id=filters['owner'])
        if filters.get('search'):
            qs = qs.filter(
                Q(cve_id__icontains=filters['search']) |
                Q(package_name__icontains=filters['search']) |
                Q(vulnerability_key__icontains=filters['search'])
            )
    total = qs.count()
    start = (page - 1) * page_size
    items = qs.select_related('owner', 'risk_accepted_by', 'verified_by')[start:start + page_size]
    return {
        'items': list(items),
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size,
    }


def get_affected_assets():
    from django.db.models import Count, Max
    assets = VulnerabilityCase.objects.values('agent_id', 'agent_name').annotate(
        vuln_count=Count('id'),
        max_cvss=Max('cvss_score'),
        critical_count=Count('id', filter=Q(priority='CRITICAL')),
    ).order_by('-vuln_count')
    return list(assets)


def get_cve_inventory():
    from django.db.models import Count, Max
    cves = VulnerabilityCase.objects.values('cve_id').annotate(
        affected_agents=Count('agent_id', distinct=True),
        max_cvss=Max('cvss_score'),
        severity=Max('severity'),
        count=Count('id'),
    ).order_by('-max_cvss')
    return list(cves)
