from vulnerabilities.models import VulnerabilityCase, VulnerabilityAuditLog


def normalize_cve_id(cve_id):
    if not cve_id:
        return ''
    cve_id = cve_id.strip().upper()
    if not cve_id.startswith('CVE-'):
        cve_id = 'CVE-' + cve_id
    return cve_id


def build_vulnerability_key(cve_id, agent_id, package_name):
    return f"{cve_id}::{agent_id}::{package_name}"


def map_severity_to_priority(severity, cvss_score=None):
    severity = (severity or '').lower()
    if severity == 'critical' or (cvss_score and cvss_score >= 9.0):
        return 'CRITICAL'
    elif severity == 'high' or (cvss_score and cvss_score >= 7.0):
        return 'HIGH'
    elif severity == 'medium' or (cvss_score and cvss_score >= 4.0):
        return 'MEDIUM'
    elif severity == 'low' or (cvss_score and cvss_score >= 0.1):
        return 'LOW'
    return 'INFO'


def sync_vulnerability_from_indexer(vuln_data, user=None):
    cve_id = normalize_cve_id(vuln_data.get('cve_id', ''))
    agent_id = vuln_data.get('agent_id', '')
    package_name = vuln_data.get('package_name', '')
    key = build_vulnerability_key(cve_id, agent_id, package_name)

    priority = map_severity_to_priority(
        vuln_data.get('severity', ''),
        vuln_data.get('cvss_score'),
    )

    case, created = VulnerabilityCase.objects.update_or_create(
        vulnerability_key=key,
        defaults={
            'agent_id': agent_id,
            'cve_id': cve_id,
            'package_name': package_name,
            'installed_version': vuln_data.get('installed_version', ''),
            'vulnerable_version': vuln_data.get('vulnerable_version', ''),
            'cvss_score': vuln_data.get('cvss_score'),
            'severity': vuln_data.get('severity', ''),
            'description': vuln_data.get('description', ''),
            'reference_url': vuln_data.get('reference', ''),
            'priority': priority,
        }
    )

    if created:
        VulnerabilityAuditLog.objects.create(
            vulnerability=case,
            user=user,
            action='Created',
            note='Synced from Wazuh vulnerability index',
        )

    return case, created
