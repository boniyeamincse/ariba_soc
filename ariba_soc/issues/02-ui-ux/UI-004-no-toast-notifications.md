# UI-004: Messages Use Dismissible Alerts Instead of Toasts

- **Severity**: Low
- **Priority**: P3 (backlog)
- **Category**: UI/UX

## Current Problem
`templates/base.html:107-116` renders Django `messages` as dismissible `.alert` divs inside the main content area. These push the page content down on every page load. On pages with many messages (e.g., after a bulk operation), the alerts can consume significant vertical space.

The `static/js/ariba-soc.js` has no toast logic — it only has a CSRF helper.

## Expected Behavior
Messages should be rendered as floating toast notifications (Bootstrap 5 toast component) fixed to the top-right corner. They should auto-dismiss after 5 seconds with a fade animation, never affecting page layout.

## Affected Files
- `templates/base.html:107-116`
- `static/js/ariba-soc.js` (needs toast initialization)

## Suggested Fix
Replace the message block in `base.html`:
```html
{% if messages %}
<div class="toast-container position-fixed top-0 end-0 p-3" style="z-index: 1080;">
    {% for message in messages %}
    <div class="toast align-items-center text-bg-{{ message.tags }} border-0" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="5000">
        <div class="d-flex">
            <div class="toast-body">{{ message }}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    </div>
    {% endfor %}
</div>
{% endif %}
```
In `ariba-soc.js`, add: `document.querySelectorAll('.toast').forEach(t => new bootstrap.Toast(t).show());`

## QA Verification
1. Perform any action that generates a success/error message → a floating toast must appear at top-right.
2. The toast must auto-fade after 5 seconds.
3. The toast must not push other page content down.
