# UI-005: Avatar Upload Has No Client-Side Preview

- **Severity**: Low
- **Priority**: P3 (backlog)
- **Category**: UI/UX

## Current Problem
`accounts/forms.py:18` defines the avatar field as:
```python
'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
```
The profile template renders this as a standard file input with no image preview. When a user selects a new avatar, they cannot see what it looks like until they submit the form and the page reloads. The navbar (`base.html:78-80`) conditionally displays the avatar but there's no preview during upload.

## Expected Behavior
When a user selects an image file, a client-side preview should appear immediately using JavaScript (FileReader API). The preview should show the image at the same 24×24px circular crop that will appear in the navbar.

## Affected Files
- `templates/ariba_soc/profile.html` (avatar field rendering)
- `static/js/ariba-soc.js` (needs preview function)

## Suggested Fix
In the profile template, add an image preview element next to the file input:
```html
<div class="d-flex align-items-center gap-3">
    <img id="avatarPreview" src="{{ profile.avatar.url|default:'' }}" 
         class="rounded-circle" style="width: 64px; height: 64px; object-fit: cover; 
         {% if not profile.avatar %}display:none{% endif %}">
    {{ form.avatar }}
</div>
```
JS:
```javascript
document.getElementById('id_avatar')?.addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = e => {
            const img = document.getElementById('avatarPreview');
            img.src = e.target.result;
            img.style.display = 'block';
        };
        reader.readAsDataURL(file);
    }
});
```

## QA Verification
1. Go to Profile page, click avatar file input, select an image.
2. Before clicking Save, the preview must show the selected image.
3. After saving, the navbar must display the new avatar.
