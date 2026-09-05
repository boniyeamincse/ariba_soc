import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .forms import LiveSearchForm
from .permissions import require_hunting_access, hunting_permission_required
from .services.hunt_executor import HuntExecutor
from .services.query_validator import decode_cursor, QueryValidationError


executor = HuntExecutor()


@require_hunting_access
def live_search_view(request):
    form = LiveSearchForm()
    return render(request, 'hunting/live_search.html', {
        'form': form,
        'is_basic': not _has_advanced(request.user),
    })


@require_POST
@hunting_permission_required('can_use_basic_hunting')
def search_api(request):
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST.dict()
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    form = LiveSearchForm(data)
    if not form.is_valid():
        return JsonResponse({'error': 'Invalid filters', 'details': form.errors}, status=400)

    filters = form.get_filters()

    if data.get('cursor'):
        try:
            cursor_data = decode_cursor(data['cursor'])
            filters['cursor'] = cursor_data
        except QueryValidationError as e:
            return JsonResponse({'error': str(e)}, status=e.status_code)

    try:
        result = executor.execute_search(filters, request.user)
    except QueryValidationError as e:
        return JsonResponse({'error': str(e)}, status=e.status_code)

    status_code = 200 if result.get('success') else 503
    return JsonResponse(result, status=status_code)


@require_hunting_access
def event_detail_api(request, event_id):
    return JsonResponse({'error': 'Event detail not available via search API'}, status=404)


def _has_advanced(user):
    from accounts.models import RolePermission
    return RolePermission.has_permission(user.analyst_profile.role, 'can_use_advanced_hunting')
