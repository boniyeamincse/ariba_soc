document.addEventListener('DOMContentLoaded', function() {
    // Toast notifications
    document.querySelectorAll('.toast').forEach(function(t) {
        var toast = new bootstrap.Toast(t);
        toast.show();
    });

    // Avatar preview
    var avatarInput = document.getElementById('id_avatar');
    if (avatarInput) {
        avatarInput.addEventListener('change', function(e) {
            var file = e.target.files[0];
            if (file) {
                var reader = new FileReader();
                reader.onload = function(ev) {
                    var preview = document.getElementById('avatarPreview');
                    if (preview) {
                        preview.src = ev.target.result;
                        preview.style.display = 'block';
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Loading state helper
    function withLoading(btnSelector, promiseFn) {
        var btn = document.querySelector(btnSelector);
        if (!btn) return promiseFn();
        var orig = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Loading...';
        return promiseFn().finally(function() {
            btn.disabled = false;
            btn.innerHTML = orig;
        });
    }

    // Wazuh sync loading
    var syncForm = document.querySelector('form[action*="wazuh_integration:sync"]');
    if (syncForm) {
        syncForm.addEventListener('submit', function(e) {
            var btn = syncForm.querySelector('button[type="submit"]');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Syncing...';
            }
        });
    }

    // Export loading
    document.querySelectorAll('.export-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            var orig = this.innerHTML;
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Exporting...';
            setTimeout(function() {
                btn.disabled = false;
                btn.innerHTML = orig;
            }, 5000);
        });
    });

    // Expandable table rows
    document.querySelectorAll('.expand-row-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            var rowId = this.getAttribute('data-row-id');
            var detailRow = document.getElementById('detail-' + rowId);
            if (detailRow) {
                detailRow.classList.toggle('d-none');
                this.querySelector('i').classList.toggle('bi-chevron-down');
                this.querySelector('i').classList.toggle('bi-chevron-up');
            }
        });
    });

    // Table row click to expand
    document.querySelectorAll('.clickable-row').forEach(function(row) {
        row.addEventListener('click', function() {
            var btn = this.querySelector('.expand-row-btn');
            if (btn) btn.click();
        });
    });

    // Edit modal - load alert data
    document.querySelectorAll('[data-bs-target="#editAlertModal"]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var alertId = this.getAttribute('data-alert-id');
            var form = document.getElementById('editAlertForm');
            if (form) form.action = form.action.replace(/\/\d+\//, '/' + alertId + '/');
            // Load alert data via API
            var alertName = this.getAttribute('data-alert-name');
            var assigneeId = this.getAttribute('data-assignee-id');
            var status = this.getAttribute('data-status');
            var severity = this.getAttribute('data-severity');
            var verdict = this.getAttribute('data-verdict');
            var priority = this.getAttribute('data-priority');

            var assigneeSelect = document.getElementById('id_assignee');
            var statusSelect = document.getElementById('id_status');
            var severitySelect = document.getElementById('id_severity');
            var verdictSelect = document.getElementById('id_verdict');
            var prioritySelect = document.getElementById('id_priority');

            if (assigneeSelect && assigneeId) assigneeSelect.value = assigneeId;
            if (statusSelect && status) statusSelect.value = status;
            if (severitySelect && severity) severitySelect.value = severity;
            if (verdictSelect && verdict) verdictSelect.value = verdict;
            if (prioritySelect && priority) prioritySelect.value = priority;
        });
    });

    // Confirm actions
    document.querySelectorAll('[data-confirm]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            if (!confirm(this.getAttribute('data-confirm') || 'Are you sure?')) {
                e.preventDefault();
            }
        });
    });

    // Kanban drag and drop (simple version)
    var kanbanCards = document.querySelectorAll('.kanban-card');
    var kanbanColumns = document.querySelectorAll('.kanban-column-body');

    kanbanCards.forEach(function(card) {
        card.setAttribute('draggable', 'true');
        card.addEventListener('dragstart', function(e) {
            e.dataTransfer.setData('text/plain', this.getAttribute('data-alert-id'));
            this.classList.add('opacity-50');
        });
        card.addEventListener('dragend', function() {
            this.classList.remove('opacity-50');
        });
    });

    kanbanColumns.forEach(function(column) {
        column.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('bg-opacity-10');
        });
        column.addEventListener('dragleave', function() {
            this.classList.remove('bg-opacity-10');
        });
        column.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('bg-opacity-10');
            var alertId = e.dataTransfer.getData('text/plain');
            var newStatus = this.getAttribute('data-status');
            var newVerdict = this.getAttribute('data-verdict');
            if (alertId && (newStatus || newVerdict)) {
                moveAlert(alertId, newStatus, newVerdict, this);
            }
        });
    });

    function moveAlert(alertId, newStatus, newVerdict, column) {
        var card = document.querySelector('.kanban-card[data-alert-id="' + alertId + '"]');
        if (!card) return;
        
        var oldColumn = card.closest('.kanban-column-body');
        column.appendChild(card);
        updateColumnCounts();

        var payload = {};
        if (newStatus) payload.status = newStatus;
        if (newVerdict) payload.verdict = newVerdict;

        fetch('/api/alerts/' + alertId + '/move/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(payload)
        })
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (!data.success) {
                if (oldColumn) {
                    oldColumn.appendChild(card);
                    updateColumnCounts();
                }
                alert('Failed to move alert: ' + (data.error || 'Unknown error'));
            } else {
                if (data.status) card.setAttribute('data-status', data.status);
                if (data.verdict) card.setAttribute('data-verdict', data.verdict);
            }
        })
        .catch(function() {
            if (oldColumn) {
                oldColumn.appendChild(card);
                updateColumnCounts();
            }
            alert('Failed to move alert due to network error.');
        });
    }

    function updateColumnCounts() {
        document.querySelectorAll('.kanban-column').forEach(function(col) {
            var cards = col.querySelectorAll('.kanban-card');
            var visibleCount = 0;
            cards.forEach(function(c) {
                if (c.style.display !== 'none') visibleCount++;
            });
            
            var badge = col.querySelector('.kanban-column-header .badge');
            if (badge) badge.textContent = visibleCount;
            
            var body = col.querySelector('.kanban-column-body');
            var emptyMsg = body.querySelector('.empty-message');
            if (visibleCount === 0) {
                if (!emptyMsg) {
                    var div = document.createElement('div');
                    div.className = 'text-center text-muted py-4 empty-message';
                    div.innerHTML = '<small>No alerts matching criteria</small>';
                    body.appendChild(div);
                }
            } else if (emptyMsg) {
                emptyMsg.remove();
            }
        });
    }

    function getCookie(name) {
        var value = '; ' + document.cookie;
        var parts = value.split('; ' + name + '=');
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    // Global alarm polling and audio playback
    var alarmBanner = document.getElementById('globalAlarmBanner');
    var alarmAudio = document.getElementById('globalAlarmAudio');
    var alarmStopBtn = document.getElementById('globalAlarmStopBtn');
    var alarmStateUrl = alarmBanner ? alarmBanner.getAttribute('data-state-url') : '';
    var alarmStopUrl = alarmBanner ? alarmBanner.getAttribute('data-stop-url') : '';
    var alarmSoundUrl = alarmBanner ? alarmBanner.getAttribute('data-sound-url') : '';
    var alarmPollingTimer = null;
    var alarmWasActive = false;

    function applyAlarmState(state) {
        if (!alarmBanner) return;
        var active = !!(state && state.active && state.enabled);
        var soundUrl = state && state.sound_url ? state.sound_url : alarmSoundUrl;
        var message = state && state.active_message ? state.active_message : 'A monitored alert triggered the alarm state.';

        alarmBanner.classList.toggle('show', active);
        document.body.classList.toggle('alarm-active', active);

        var alarmMessage = document.getElementById('globalAlarmMessage');
        if (alarmMessage) {
            alarmMessage.textContent = message;
        }

        if (alarmAudio) {
            if (soundUrl && alarmAudio.getAttribute('src') !== soundUrl) {
                alarmAudio.setAttribute('src', soundUrl);
                alarmAudio.load();
            }
            if (active) {
                if (!alarmWasActive) {
                    alarmAudio.currentTime = 0;
                    alarmAudio.play().catch(function() {});
                } else if (alarmAudio.paused) {
                    alarmAudio.play().catch(function() {});
                }
            } else {
                alarmAudio.pause();
                alarmAudio.currentTime = 0;
            }
        }

        alarmWasActive = active;
    }

    function refreshAlarmState() {
        if (!alarmStateUrl) return;
        fetch(alarmStateUrl, {
            credentials: 'same-origin',
            headers: {
                'Accept': 'application/json'
            }
        })
        .then(function(response) { return response.ok ? response.json() : null; })
        .then(function(data) {
            if (data) applyAlarmState(data);
        })
        .catch(function() {});
    }

    if (alarmBanner && alarmStateUrl) {
        refreshAlarmState();
        alarmPollingTimer = setInterval(refreshAlarmState, 3000);
    }

    if (alarmStopBtn && alarmStopUrl) {
        alarmStopBtn.addEventListener('click', function() {
            fetch(alarmStopUrl, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                }
            })
            .then(function(response) { return response.ok ? response.json() : null; })
            .then(function(data) {
                if (data) applyAlarmState(data);
            })
            .catch(function() {});
        });
    }

    // Filter form auto-submit
    document.querySelectorAll('.filter-auto-submit').forEach(function(el) {
        el.addEventListener('change', function() {
            this.closest('form').submit();
        });
    });

    // Sidebar toggle
    var sidebarToggle = document.querySelector('.sidebar-toggler');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            document.getElementById('sidebar').classList.toggle('show');
        });
    }

    // Sidebar overlay
    var sidebarOverlay = document.getElementById('sidebarOverlay');
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function() {
            document.getElementById('sidebar').classList.remove('show');
        });
    }

    // Topbar hamburger toggle
    document.querySelectorAll('.ariba-topbar .btn-link').forEach(function(btn) {
        btn.addEventListener('click', function() {
            document.getElementById('sidebar').classList.toggle('show');
        });
    });

    // Active sidebar link based on current URL
    var currentPath = window.location.pathname;
    document.querySelectorAll('.sidebar-nav .nav-link, .sidebar-nav-sub .nav-link').forEach(function(link) {
        var href = link.getAttribute('href');
        if (href && currentPath.startsWith(href) && href !== '/') {
            link.classList.add('active');
        }
    });

    // Auto-expand Settings menu if on a settings page
    if (currentPath.startsWith('/settings/')) {
        var settingsCollapse = document.getElementById('settingsMenu');
        if (settingsCollapse) {
            var bsCollapse = new bootstrap.Collapse(settingsCollapse, {toggle: false});
            bsCollapse.show();
            var toggle = document.querySelector('.nav-collapse-toggle');
            if (toggle) toggle.setAttribute('aria-expanded', 'true');
        }
    }

    // Date range presets
    document.querySelectorAll('[data-date-preset]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var preset = this.getAttribute('data-date-preset');
            var now = new Date();
            var from = new Date();
            switch(preset) {
                case 'today': from.setHours(0,0,0,0); break;
                case '7d': from.setDate(from.getDate() - 7); break;
                case '30d': from.setDate(from.getDate() - 30); break;
                case '90d': from.setDate(from.getDate() - 90); break;
            }
            document.getElementById('id_date_from').value = from.toISOString().slice(0,16);
            document.getElementById('id_date_to').value = now.toISOString().slice(0,16);
        });
    });
});

    // Kanban quick filters
    var currentUserId = document.body.getAttribute('data-user-id');
    document.querySelectorAll('.board-filter-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var filter = this.getAttribute('data-filter');
            
            // Toggle active state
            document.querySelectorAll('.board-filter-btn').forEach(function(b) { b.classList.remove('active'); });
            this.classList.add('active');

            var cards = document.querySelectorAll('.kanban-card');
            cards.forEach(function(card) {
                var show = true;
                var sev = (card.getAttribute('data-severity') || '').trim().toLowerCase();
                if (filter === 'mine') {
                    show = (card.getAttribute('data-assignee-id') === currentUserId);
                } else if (filter === 'critical') {
                    show = (sev === 'critical');
                } else if (filter === 'high') {
                    show = (sev === 'high');
                } else if (filter === 'medium') {
                    show = (sev === 'medium');
                } else if (filter === 'low') {
                    show = (sev === 'low');
                } else if (filter === 'clear') {
                    show = true;
                }
                
                card.style.display = show ? 'block' : 'none';
            });
            
            updateColumnCounts();
        });
    });

    // Kanban Board View Mode Toggles (Active Triage vs Closed vs All)
    document.querySelectorAll('.board-view-toggle').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var viewMode = this.getAttribute('data-view-mode');
            document.querySelectorAll('.board-view-toggle').forEach(function(b) { b.classList.remove('active', 'btn-info', 'btn-primary'); b.classList.add('btn-outline-secondary'); });
            this.classList.remove('btn-outline-secondary');
            this.classList.add('active', 'btn-primary');

            var activeCols = document.querySelectorAll('.board-col-active-group');
            var closedCols = document.querySelectorAll('.board-col-closed-group');

            if (viewMode === 'active') {
                activeCols.forEach(function(c) { c.style.display = ''; });
                closedCols.forEach(function(c) { c.style.display = 'none'; });
            } else if (viewMode === 'closed') {
                activeCols.forEach(function(c) { c.style.display = 'none'; });
                closedCols.forEach(function(c) { c.style.display = ''; });
            } else {
                activeCols.forEach(function(c) { c.style.display = ''; });
                closedCols.forEach(function(c) { c.style.display = ''; });
            }
        });
    });
