from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import VulnerabilityCase, VulnerabilityAuditLog, ALLOWED_TRANSITIONS
from .forms import VulnerabilityFilterForm, AssignForm, RemediationNoteForm, RiskAcceptanceForm, ReopenForm
from .permissions import require_vuln_access
from .services.dashboard_metrics import get_overview_metrics, get_inventory, get_affected_assets, get_cve_inventory
from .services.remediation import (
    assign_case, start_progress, await_patch, await_verification,
    resolve_case, accept_risk, mark_false_positive, reopen_case, add_note,
    RemediationError,
)
from .services.wazuh_reader import WazuhVulnerabilityReader


@require_vuln_access
def overview(request):
    metrics = get_overview_metrics()
    return render(request, 'vulnerabilities/overview.html', {'metrics': metrics})


@require_vuln_access
def inventory(request):
    form = VulnerabilityFilterForm(request.GET)
    filters = form.cleaned_data if form.is_valid() else {}
    page = int(request.GET.get('page', 1))
    data = get_inventory(filters, page=page)
    return render(request, 'vulnerabilities/inventory.html', {
        'form': form,
        'items': data['items'],
        'total': data['total'],
        'page': data['page'],
        'total_pages': data['total_pages'],
    })


@require_vuln_access
def affected_assets(request):
    assets = get_affected_assets()
    return render(request, 'vulnerabilities/affected_assets.html', {'assets': assets})


@require_vuln_access
def cve_list(request):
    cves = get_cve_inventory()
    return render(request, 'vulnerabilities/cve_list.html', {'cves': cves})


@require_vuln_access
def detail(request, key):
    case = get_object_or_404(VulnerabilityCase, vulnerability_key=key)
    audit_logs = case.audit_logs.select_related('user')[:20]
    allowed = ALLOWED_TRANSITIONS.get(case.status, [])
    return render(request, 'vulnerabilities/detail.html', {
        'case': case,
        'audit_logs': audit_logs,
        'allowed_transitions': allowed,
        'assign_form': AssignForm(),
        'note_form': RemediationNoteForm(initial={'remediation_note': case.remediation_note}),
        'risk_form': RiskAcceptanceForm(),
        'reopen_form': ReopenForm(),
    })


@require_vuln_access
def assign_view(request, key):
    case = get_object_or_404(VulnerabilityCase, vulnerability_key=key)
    if request.method == 'POST':
        owner_id = request.POST.get('owner')
        try:
            owner = User.objects.get(id=owner_id)
            assign_case(case, request.user, owner)
            messages.success(request, f'Assigned to {owner.username}')
        except (User.DoesNotExist, RemediationError) as e:
            messages.error(request, str(e))
    return redirect('vulnerabilities:detail', key=key)


@require_vuln_access
def remediate_view(request, key):
    case = get_object_or_404(VulnerabilityCase, vulnerability_key=key)
    if request.method == 'POST':
        form = RemediationNoteForm(request.POST)
        if form.is_valid():
            try:
                action = request.POST.get('action', 'note')
                if action == 'start':
                    start_progress(case, request.user)
                elif action == 'await_patch':
                    await_patch(case, request.user)
                elif action == 'await_verification':
                    await_verification(case, request.user)
                elif action == 'resolve':
                    resolve_case(case, request.user)
                add_note(case, request.user, form.cleaned_data['remediation_note'])
                messages.success(request, 'Remediation updated')
            except RemediationError as e:
                messages.error(request, str(e))
    return redirect('vulnerabilities:detail', key=key)


@require_vuln_access
def accept_risk_view(request, key):
    case = get_object_or_404(VulnerabilityCase, vulnerability_key=key)
    if request.method == 'POST':
        form = RiskAcceptanceForm(request.POST)
        if form.is_valid():
            try:
                accept_risk(case, request.user, form.cleaned_data['reason'])
                messages.success(request, 'Risk accepted')
            except RemediationError as e:
                messages.error(request, str(e))
    return redirect('vulnerabilities:detail', key=key)


@require_vuln_access
def verify_view(request, key):
    case = get_object_or_404(VulnerabilityCase, vulnerability_key=key)
    if request.method == 'POST':
        try:
            resolve_case(case, request.user)
            messages.success(request, 'Vulnerability verified and resolved')
        except RemediationError as e:
            messages.error(request, str(e))
    return redirect('vulnerabilities:detail', key=key)


@require_vuln_access
def reopen_view(request, key):
    case = get_object_or_404(VulnerabilityCase, vulnerability_key=key)
    if request.method == 'POST':
        form = ReopenForm(request.POST)
        if form.is_valid():
            try:
                reopen_case(case, request.user, form.cleaned_data.get('reason', ''))
                messages.success(request, 'Vulnerability reopened')
            except RemediationError as e:
                messages.error(request, str(e))
    return redirect('vulnerabilities:detail', key=key)


@require_vuln_access
def false_positive_view(request, key):
    case = get_object_or_404(VulnerabilityCase, vulnerability_key=key)
    if request.method == 'POST':
        try:
            mark_false_positive(case, request.user, request.POST.get('reason', ''))
            messages.success(request, 'Marked as false positive')
        except RemediationError as e:
            messages.error(request, str(e))
    return redirect('vulnerabilities:detail', key=key)


@require_vuln_access
def sync_from_wazuh(request):
    if request.method == 'POST':
        reader = WazuhVulnerabilityReader()
        result = reader.fetch_vulnerabilities(size=1000)
        if result.get('success'):
            from .services.normalizer import sync_vulnerability_from_indexer
            created = 0
            updated = 0
            for vuln in result.get('vulnerabilities', []):
                _, was_created = sync_vulnerability_from_indexer(vuln, request.user)
                if was_created:
                    created += 1
                else:
                    updated += 1
            messages.success(request, f'Synced {len(result["vulnerabilities"])} vulnerabilities ({created} new, {updated} updated)')
        else:
            messages.error(request, result.get('message', 'Sync failed'))
    return redirect('vulnerabilities:overview')
