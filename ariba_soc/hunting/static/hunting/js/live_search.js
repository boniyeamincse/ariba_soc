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
        setEmptyState('Ready to search', 'Choose a time range and filters, then run a live search.');
        resultCount.textContent = '0 events';
        errorAlert.style.display = 'none';
        lastUpdated.textContent = 'Ready';
        currentCursor = null;
    });

    btnNextPage.addEventListener('click', function() {
        if (currentCursor && !isSearching) executeSearch(currentCursor);
    });

    function executeSearch(cursor) {
        isSearching = true;
        searchBtn.disabled = true;
        btnNextPage.disabled = true;
        btnNextPage.style.display = 'none';
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
                lastUpdated.textContent = new Date().toLocaleString();
            } else {
                showError(result.data.error || result.data.message || 'Search failed');
                if (result.status === 503) {
                    setEmptyState('Indexer unavailable', 'The Wazuh Indexer is temporarily unavailable. Try again in a moment.');
                }
            }
        })
        .catch(function(err) {
            loading.style.display = 'none';
            isSearching = false;
            searchBtn.disabled = false;
            btnNextPage.disabled = true;
            showError('Network error: ' + err.message);
            setEmptyState('Search failed', 'A network error prevented the query from completing.');
        });
    }

    function renderResults(data) {
        resultCount.textContent = data.total + ' events (returned ' + data.returned + ')';

        if (!data.events || data.events.length === 0) {
            setEmptyState('No events found', 'Try broadening the time range or adjusting the approved filters.');
            return;
        }

        resultsBody.innerHTML = '';
        data.events.forEach(function(evt) {
            const tr = document.createElement('tr');
            tr.appendChild(createCell(evt.timestamp || ''));
            tr.appendChild(createCell(String(evt.rule_level || '')));
            tr.appendChild(createSeverityCell(evt.severity || ''));
            tr.appendChild(createPivotCell(evt.rule_id || '', 'id_rule_id'));
            tr.appendChild(createCell(evt.rule_description || '', true));
            tr.appendChild(createCell(evt.agent_name || evt.agent_id || ''));
            tr.appendChild(createPivotCell(evt.source_ip || '', 'id_source_ip'));
            tr.appendChild(createPivotCell(evt.destination_ip || '', 'id_destination_ip'));
            tr.appendChild(createPivotCell(evt.username || '', 'id_username'));
            tr.appendChild(createCell(evt.mitre_id || ''));
            tr.appendChild(createActionCell(evt.raw_event || {}));
            resultsBody.appendChild(tr);
        });

        currentCursor = data.next_cursor;
        btnNextPage.disabled = !currentCursor;
        btnNextPage.style.display = currentCursor ? '' : 'none';
    }

    function showError(msg) {
        errorAlert.textContent = msg;
        errorAlert.style.display = '';
    }

    function createCell(value, titleOnly) {
        const td = document.createElement('td');
        if (titleOnly && value) {
            td.title = value;
        }
        td.textContent = value;
        return td;
    }

    function createPivotCell(value, fieldId) {
        const td = document.createElement('td');
        if (!value) return td;
        const a = document.createElement('a');
        a.href = '#';
        a.className = 'text-info text-decoration-none';
        a.textContent = value;
        a.title = 'Pivot search';
        a.addEventListener('click', function(e) {
            e.preventDefault();
            const input = document.getElementById(fieldId);
            if (input) {
                input.value = value;
                const form = document.getElementById('hunt-search-form');
                form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
            }
        });
        td.appendChild(a);
        return td;
    }

    function createSeverityCell(value) {
        const td = document.createElement('td');
        const badge = document.createElement('span');
        const normalized = String(value || '').toLowerCase();
        badge.className = 'severity-' + normalized;
        badge.textContent = value || 'Unknown';
        td.appendChild(badge);
        return td;
    }

    function createActionCell(rawEvent) {
        const td = document.createElement('td');
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn btn-sm btn-outline-info';
        button.innerHTML = '<i class="bi bi-eye me-1"></i>View Event';
        button.addEventListener('click', function() {
            try {
                eventJson.textContent = JSON.stringify(rawEvent || {}, null, 2);
            } catch (e) {
                eventJson.textContent = 'Unable to render event data';
            }
            eventModal.show();
        });
        td.appendChild(button);
        return td;
    }

    function setEmptyState(title, text) {
        resultsBody.innerHTML = '';
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 11;
        const wrapper = document.createElement('div');
        wrapper.className = 'hunt-empty';

        const icon = document.createElement('i');
        icon.className = 'bi bi-search';
        const heading = document.createElement('div');
        heading.className = 'hunt-empty__title';
        heading.textContent = title;
        const body = document.createElement('div');
        body.className = 'hunt-empty__text';
        body.textContent = text;

        wrapper.appendChild(icon);
        wrapper.appendChild(heading);
        wrapper.appendChild(body);
        td.appendChild(wrapper);
        tr.appendChild(td);
        resultsBody.appendChild(tr);
    }

    toggleCustomRange();
})();
