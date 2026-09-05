(function() {
    'use strict';

    const form = document.getElementById('hunt-search-form');
    const searchBtn = document.getElementById('btn-search');
    const resetBtn = document.getElementById('btn-reset');
    const timeRange = document.getElementById('time-range');
    const customStart = document.getElementById('custom-start-group');
    const customEnd = document.getElementById('custom-end-group');
    const loading = document.getElementById('loading-spinner');
    const errorAlert = document.getElementById('error-alert');
    const resultsBody = document.getElementById('results-body');
    const resultCount = document.getElementById('result-count');
    const paginationFooter = document.getElementById('pagination-footer');
    const btnNextPage = document.getElementById('btn-next-page');
    const lastUpdated = document.getElementById('last-updated');
    const eventModal = new bootstrap.Modal(document.getElementById('eventModal'));
    const eventJson = document.getElementById('event-json');

    let currentCursor = null;
    let isSearching = false;

    function toggleCustomRange() {
        const show = timeRange.value === 'custom';
        customStart.style.display = show ? '' : 'none';
        customEnd.style.display = show ? '' : 'none';
    }

    timeRange.addEventListener('change', toggleCustomRange);

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        if (isSearching) return;
        currentCursor = null;
        executeSearch();
    });

    resetBtn.addEventListener('click', function() {
        form.reset();
        toggleCustomRange();
        resultsBody.innerHTML = '<tr><td colspan="11" class="text-center text-muted py-4">Enter filters and click Search</td></tr>';
        resultCount.textContent = '0 events';
        paginationFooter.style.display = 'none';
        errorAlert.style.display = 'none';
        currentCursor = null;
    });

    btnNextPage.addEventListener('click', function() {
        if (currentCursor && !isSearching) executeSearch(currentCursor);
    });

    function executeSearch(cursor) {
        isSearching = true;
        searchBtn.disabled = true;
        loading.style.display = '';
        errorAlert.style.display = 'none';

        const formData = new FormData(form);
        const params = {};
        formData.forEach(function(value, key) {
            if (value) params[key] = value;
        });
        if (cursor) params.cursor = cursor;

        fetch('/hunting/api/search/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value,
            },
            body: JSON.stringify(params),
        })
        .then(function(response) {
            return response.json().then(function(data) {
                return { status: response.status, data: data };
            });
        })
        .then(function(result) {
            loading.style.display = 'none';
            isSearching = false;
            searchBtn.disabled = false;

            if (result.status === 200 && result.data.success) {
                renderResults(result.data);
                lastUpdated.textContent = 'Updated: ' + new Date().toLocaleTimeString();
            } else {
                showError(result.data.error || result.data.message || 'Search failed');
            }
        })
        .catch(function(err) {
            loading.style.display = 'none';
            isSearching = false;
            searchBtn.disabled = false;
            showError('Network error: ' + err.message);
        });
    }

    function renderResults(data) {
        resultCount.textContent = data.total + ' events (returned ' + data.returned + ')';
        resultsBody.innerHTML = '';

        if (!data.events || data.events.length === 0) {
            resultsBody.innerHTML = '<tr><td colspan="11" class="text-center text-muted py-4">No events found</td></tr>';
            paginationFooter.style.display = 'none';
            return;
        }

        data.events.forEach(function(evt) {
            const tr = document.createElement('tr');
            const sevClass = 'severity-' + (evt.severity || '').toLowerCase();
            tr.innerHTML =
                '<td>' + escapeHtml(evt.timestamp || '') + '</td>' +
                '<td>' + escapeHtml(String(evt.rule_level || '')) + '</td>' +
                '<td><span class="' + sevClass + '">' + escapeHtml(evt.severity || '') + '</span></td>' +
                '<td>' + escapeHtml(evt.rule_id || '') + '</td>' +
                '<td title="' + escapeHtml(evt.rule_description || '') + '">' + escapeHtml(evt.rule_description || '') + '</td>' +
                '<td>' + escapeHtml(evt.agent_name || evt.agent_id || '') + '</td>' +
                '<td>' + escapeHtml(evt.source_ip || '') + '</td>' +
                '<td>' + escapeHtml(evt.destination_ip || '') + '</td>' +
                '<td>' + escapeHtml(evt.username || '') + '</td>' +
                '<td>' + escapeHtml(evt.mitre_id || '') + '</td>' +
                '<td><button class="btn btn-sm btn-outline-info btn-view-event" data-event=\'' + escapeHtml(JSON.stringify(evt.raw_event || {})) + '\'><i class="fas fa-eye"></i></button></td>';
            resultsBody.appendChild(tr);
        });

        document.querySelectorAll('.btn-view-event').forEach(function(btn) {
            btn.addEventListener('click', function() {
                try {
                    const eventData = JSON.parse(this.getAttribute('data-event'));
                    eventJson.textContent = JSON.stringify(eventData, null, 2);
                } catch(e) {
                    eventJson.textContent = 'Unable to parse event data';
                }
                eventModal.show();
            });
        });

        currentCursor = data.next_cursor;
        paginationFooter.style.display = currentCursor ? '' : 'none';
        btnNextPage.disabled = !currentCursor;
    }

    function showError(msg) {
        errorAlert.textContent = msg;
        errorAlert.style.display = '';
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    toggleCustomRange();
})();
