from django.db import migrations


def seed_default_soc_teams(apps, schema_editor):
    SocTeam = apps.get_model('accounts', 'SocTeam')
    AnalystProfile = apps.get_model('accounts', 'AnalystProfile')

    default_teams = [
        {
            'name': 'Tier 1 Triage Alpha',
            'slug': 'tier-1-triage-alpha',
            'tier': 'L1',
            'shift_type': 'MORNING',
            'description': 'Primary frontline 24/7 triage and alert qualification team (Morning shift).',
        },
        {
            'name': 'Tier 1 Triage Bravo',
            'slug': 'tier-1-triage-bravo',
            'tier': 'L1',
            'shift_type': 'EVENING',
            'description': 'Primary frontline 24/7 triage and alert qualification team (Evening shift).',
        },
        {
            'name': 'Tier 1 Triage Charlie',
            'slug': 'tier-1-triage-charlie',
            'tier': 'L1',
            'shift_type': 'NIGHT',
            'description': 'Primary frontline 24/7 triage and alert qualification team (Night shift).',
        },
        {
            'name': 'Tier 2 Incident Response (DFIR)',
            'slug': 'tier-2-incident-response',
            'tier': 'L2',
            'shift_type': 'GENERAL',
            'description': 'Deep-dive investigation, containment, digital forensics, and incident handling.',
        },
        {
            'name': 'Tier 3 Threat Hunting & Intel',
            'slug': 'tier-3-threat-hunting',
            'tier': 'L3',
            'shift_type': 'GENERAL',
            'description': 'Proactive threat hunting, IOC hypothesis validation, and threat intelligence synthesis.',
        },
        {
            'name': 'Detection Engineering',
            'slug': 'detection-engineering',
            'tier': 'ENG',
            'shift_type': 'GENERAL',
            'description': 'Wazuh rules tuning, active response SOAR scripts, and detection coverage optimization.',
        },
        {
            'name': 'SOC Leadership & Governance',
            'slug': 'soc-leadership-governance',
            'tier': 'MGMT',
            'shift_type': 'GENERAL',
            'description': 'SOC Manager, escalation governance, compliance reporting, and executive reviews.',
        },
    ]

    team_objs = {}
    for team_data in default_teams:
        team, _ = SocTeam.objects.get_or_create(slug=team_data['slug'], defaults=team_data)
        team_objs[team.tier] = team

    # Backfill existing profiles based on legacy team text choice
    for profile in AnalystProfile.objects.all():
        legacy_team = profile.team or profile.role
        if legacy_team in team_objs:
            profile.soc_team = team_objs[legacy_team]
            profile.save(update_fields=['soc_team'])
        elif legacy_team == 'L1' and 'L1' in team_objs:
            profile.soc_team = team_objs['L1']
            profile.save(update_fields=['soc_team'])


def unseed_default_soc_teams(apps, schema_editor):
    SocTeam = apps.get_model('accounts', 'SocTeam')
    SocTeam.objects.filter(slug__in=[
        'tier-1-triage-alpha',
        'tier-1-triage-bravo',
        'tier-1-triage-charlie',
        'tier-2-incident-response',
        'tier-3-threat-hunting',
        'detection-engineering',
        'soc-leadership-governance',
    ]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_socteam_analystprofile_soc_team'),
    ]

    operations = [
        migrations.RunPython(seed_default_soc_teams, unseed_default_soc_teams),
    ]
