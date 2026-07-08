import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from alerts.models import Alert, AlertSource, AlertComment, AlertAuditLog
from accounts.models import AnalystProfile

SAMPLE_ALERTS = [
    {'name': 'Windows RDP Bruteforce', 'severity': 'Critical', 'rule_level': 12, 'rule_id': '5710', 'mitre_id': 'T1110', 'mitre_tactic': 'Credential Access', 'mitre_technique': 'Brute Force', 'description': 'Multiple RDP authentication failures detected from external IP.'},
    {'name': 'Potential Data Exfiltration', 'severity': 'Critical', 'rule_level': 14, 'rule_id': '8721', 'mitre_id': 'T1048', 'mitre_tactic': 'Exfiltration', 'mitre_technique': 'Exfiltration Over Alternative Protocol', 'description': 'Large outbound data transfer detected.'},
    {'name': 'Unusual Login Location', 'severity': 'Medium', 'rule_level': 6, 'rule_id': '2351', 'mitre_id': 'T1078', 'mitre_tactic': 'Initial Access', 'mitre_technique': 'Valid Accounts', 'description': 'User logged in from an unusual geographic location.'},
    {'name': 'Email Marked as Phishing', 'severity': 'High', 'rule_level': 10, 'rule_id': '4412', 'mitre_id': 'T1566', 'mitre_tactic': 'Initial Access', 'mitre_technique': 'Phishing', 'description': 'User reported a suspicious email as phishing.'},
    {'name': 'Unapproved Mimikatz Usage', 'severity': 'Critical', 'rule_level': 15, 'rule_id': '897', 'mitre_id': 'T1003', 'mitre_tactic': 'Credential Access', 'mitre_technique': 'OS Credential Dumping', 'description': 'Mimikatz activity detected on endpoint.'},
    {'name': 'Adware Infection of PC-1273', 'severity': 'Medium', 'rule_level': 5, 'rule_id': '3321', 'description': 'Adware signature detected on host.'},
    {'name': 'Double-Extension File Creation', 'severity': 'High', 'rule_level': 9, 'rule_id': '921', 'mitre_id': 'T1204', 'mitre_tactic': 'Execution', 'mitre_technique': 'User Execution', 'description': 'File with double extension created, possible phishing payload.'},
    {'name': 'Download from GitHub Repository', 'severity': 'Low', 'rule_level': 3, 'rule_id': '1102', 'description': 'File downloaded from GitHub repository.'},
    {'name': 'Brute Force Attack from External', 'severity': 'High', 'rule_level': 10, 'rule_id': '5712', 'mitre_id': 'T1110', 'mitre_tactic': 'Credential Access', 'mitre_technique': 'Brute Force', 'description': 'Multiple failed authentication attempts from external source.'},
    {'name': 'Suspicious PowerShell Command', 'severity': 'High', 'rule_level': 8, 'rule_id': '2810', 'mitre_id': 'T1059', 'mitre_tactic': 'Execution', 'mitre_technique': 'Command and Scripting Interpreter', 'description': 'PowerShell executed with suspicious parameters.'},
    {'name': 'Linux SSH Brute Force', 'severity': 'High', 'rule_level': 9, 'rule_id': '5715', 'mitre_id': 'T1110', 'mitre_tactic': 'Credential Access', 'mitre_technique': 'Brute Force', 'description': 'Multiple SSH authentication failures detected.'},
    {'name': 'Malware Hash Detected', 'severity': 'Critical', 'rule_level': 13, 'rule_id': '6512', 'mitre_id': 'T1204', 'mitre_tactic': 'Execution', 'mitre_technique': 'User Execution', 'description': 'Known malware hash detected on endpoint.'},
    {'name': 'Admin Login from New Location', 'severity': 'Medium', 'rule_level': 7, 'rule_id': '2355', 'description': 'Administrator account logged in from unfamiliar location.'},
    {'name': 'Multiple Failed Login Attempts', 'severity': 'Medium', 'rule_level': 6, 'rule_id': '5501', 'description': 'Multiple failed login attempts detected.'},
    {'name': 'Unusual VPN Login Location', 'severity': 'Medium', 'rule_level': 6, 'rule_id': '2352', 'description': 'VPN login from unusual geographic location.'},
    {'name': 'Suspicious Scheduled Task Creation', 'severity': 'High', 'rule_level': 9, 'rule_id': '7150', 'mitre_id': 'T1053', 'mitre_tactic': 'Persistence', 'mitre_technique': 'Scheduled Task', 'description': 'Suspicious scheduled task created on endpoint.'},
    {'name': 'Malicious Web Shell Detected', 'severity': 'Critical', 'rule_level': 13, 'rule_id': '9811', 'mitre_id': 'T1505', 'mitre_tactic': 'Persistence', 'mitre_technique': 'Web Shell', 'description': 'Web shell detected on web server.'},
    {'name': 'USB Device Anomaly', 'severity': 'Medium', 'rule_level': 5, 'rule_id': '4120', 'description': 'Unknown USB device connected to workstation.'},
    {'name': 'DNS Tunneling Detected', 'severity': 'High', 'rule_level': 10, 'rule_id': '5413', 'mitre_id': 'T1572', 'mitre_tactic': 'Command and Control', 'mitre_technique': 'DNS Tunneling', 'description': 'Suspicious DNS queries indicating tunneling detected.'},
    {'name': 'Unauthorized Registry Change', 'severity': 'Medium', 'rule_level': 7, 'rule_id': '6631', 'mitre_id': 'T1112', 'mitre_tactic': 'Defense Evasion', 'mitre_technique': 'Modify Registry', 'description': 'Critical registry key modified without authorization.'},
    {'name': 'Mass File Renaming Detected', 'severity': 'High', 'rule_level': 8, 'rule_id': '5512', 'mitre_id': 'T1486', 'mitre_tactic': 'Impact', 'mitre_technique': 'Data Encrypted for Impact', 'description': 'Multiple files being renamed rapidly, possible ransomware.'},
    {'name': 'Privilege Escalation Attempt', 'severity': 'Critical', 'rule_level': 12, 'rule_id': '2310', 'mitre_id': 'T1068', 'mitre_tactic': 'Privilege Escalation', 'mitre_technique': 'Exploitation for Privilege Escalation', 'description': 'Privilege escalation attempt detected via known exploit.'},
    {'name': 'Outbound Connection to Malicious IP', 'severity': 'High', 'rule_level': 10, 'rule_id': '7211', 'mitre_id': 'T1071', 'mitre_tactic': 'Command and Control', 'mitre_technique': 'Application Layer Protocol', 'description': 'Outbound connection established to known malicious IP address.'},
    {'name': 'Service Account Anomaly', 'severity': 'Medium', 'rule_level': 6, 'rule_id': '3342', 'description': 'Service account logged in outside normal operating hours.'},
    {'name': 'Pass-the-Hash Attack Detected', 'severity': 'Critical', 'rule_level': 14, 'rule_id': '6734', 'mitre_id': 'T1550', 'mitre_tactic': 'Lateral Movement', 'mitre_technique': 'Pass the Hash', 'description': 'Pass-the-hash attack detected on domain controller.'},
]

HOSTNAMES = ['LPT-HR-009', 'LPT-HR-012', 'SRV-DC-001', 'SRV-EXCH-001', 'LPT-IT-045', 'SRV-DB-002', 'LPT-ACCT-018', 'LPT-EXEC-003', 'SRV-WEB-005', 'LPT-DEV-022']
USERNAMES = ['S.Conway', 'J.Adams', 'M.Taylor', 'R.Patel', 'K.Chen', 'L.Williams', 'D.Johnson', 'A.Martinez', 'C.Lee', 'P.Anderson']
PROCESSES = ['chrome.exe', 'powershell.exe', 'rundll32.exe', 'svchost.exe', 'outlook.exe', 'winword.exe', 'cmd.exe', 'mshta.exe', 'wscript.exe', 'explorer.exe']
SOURCE_IPS = ['185.220.101.x', '103.235.46.x', '45.33.32.x', '91.121.87.x', '192.168.1.100', '10.0.0.50', '172.16.0.25', '203.0.113.x']


class Command(BaseCommand):
    help = 'Seed sample alerts for development'

    def handle(self, *args, **options):
        source, _ = AlertSource.objects.get_or_create(name='Wazuh', source_type='Wazuh')
        users = list(User.objects.all())
        if not users:
            self.stdout.write(self.style.WARNING('No users found. Create users first.'))
            return

        for i, sample in enumerate(SAMPLE_ALERTS):
            created = timezone.now() - timedelta(hours=random.randint(1, 72), minutes=random.randint(0, 59))
            severity = sample['severity']
            if severity == 'Critical':
                status_choices = ['New', 'In Progress', 'Escalated', 'Closed']
            elif severity == 'High':
                status_choices = ['New', 'In Progress', 'Escalated']
            elif severity == 'Medium':
                status_choices = ['New', 'In Progress', 'Closed']
            else:
                status_choices = ['New', 'Closed']

            status = random.choice(status_choices)
            verdict = 'None'
            if status == 'Closed':
                verdict = random.choice(['True Positive', 'False Positive', 'Benign Positive'])
            elif status == 'Escalated':
                verdict = 'Suspicious'

            assignee = None
            assigned_at = None
            if status in ('In Progress', 'Escalated', 'Closed'):
                assignee = random.choice(users)
                assigned_at = created + timedelta(minutes=random.randint(5, 120))

            hostname = random.choice(HOSTNAMES)
            username = random.choice(USERNAMES)
            process = random.choice(PROCESSES)

            alert = Alert.objects.create(
                wazuh_alert_id=f'wz-{1000 + i}',
                alert_time=created,
                event_time=created - timedelta(minutes=random.randint(1, 5)),
                alert_name=sample['name'],
                description=sample.get('description', ''),
                severity=severity,
                severity_score=sample.get('rule_level', 5),
                status=status,
                verdict=verdict,
                priority=severity,
                source=source,
                source_name='Wazuh',
                rule_id=sample.get('rule_id', ''),
                rule_level=sample.get('rule_level', 5),
                agent_id=f'{random.randint(1, 200):03d}',
                agent_name=f'AGENT-{random.randint(1, 200):04d}',
                hostname=hostname,
                source_ip=random.choice(SOURCE_IPS),
                destination_ip='10.0.0.1',
                username=username,
                process_name=process,
                process_user=username,
                command_line=f'"{process}" -someparam value',
                target_file=f'C:\\Users\\{username}\\Downloads\\file{random.randint(1, 999)}.exe',
                file_hash_md5=''.join(random.choices('0123456789abcdef', k=32)),
                file_hash_sha256=''.join(random.choices('0123456789abcdef', k=64)),
                mitre_id=sample.get('mitre_id', ''),
                mitre_tactic=sample.get('mitre_tactic', ''),
                mitre_technique=sample.get('mitre_technique', ''),
                assignee=assignee,
                assigned_by=assignee,
                assigned_at=assigned_at,
                acknowledged_at=assigned_at,
                full_log=f'Sample full log for alert {sample["name"]}',
                alert_fields={'hostname': hostname, 'username': username},
            )

            if assignee:
                AlertAuditLog.objects.create(
                    alert=alert, user=assignee, action='Assigned', new_value=assignee.username
                )
            if status == 'Closed':
                AlertComment.objects.create(
                    alert=alert, user=assignee or random.choice(users),
                    comment=f'Alert closed as {verdict}. Investigation completed.',
                    comment_type='Closure Note'
                )
                alert.closed_at = created + timedelta(hours=random.randint(1, 12))
                alert.closure_reason = f'Closed as {verdict}'
                alert.save(update_fields=['closed_at', 'closure_reason'])
                AlertAuditLog.objects.create(
                    alert=alert, user=assignee or random.choice(users), action='Closed',
                    new_value=f'Closed as {verdict}'
                )

            self.stdout.write(self.style.SUCCESS(f'Created alert: [{severity}] {sample["name"]}'))

        self.stdout.write(self.style.SUCCESS(f'Seeded {len(SAMPLE_ALERTS)} sample alerts.'))
