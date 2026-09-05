from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from alerts.models import AlertAuditLog


@login_required
def audit_log_list(request):
    logs = AlertAuditLog.objects.select_related('user', 'alert').all()
    paginator = Paginator(logs, 100)
    page = request.GET.get('page', 1)
    return render(request, 'ariba_soc/audit_logs.html', {'logs': paginator.get_page(page)})
