# Contribution Guide

## Coding Standards

### Python

- Follow **PEP 8** style guide
- Use 4-space indentation (no tabs)
- Maximum line length: 119 characters (Django default)
- Use descriptive variable names (avoid single-letter names except in comprehensions)
- Imports order: standard library → Django → third-party → local (each group separated by blank line)
- Type hints encouraged on function signatures
- Docstrings for all public functions and classes (Google style)

### Django Conventions

- App names: lowercase with underscores (e.g., `wazuh_integration`)
- Model class names: PascalCase, singular (e.g., `WazuhManagerConfig`)
- View function names: snake_case (e.g., `alert_table`, `force_sync`)
- URL names: hyphenated (e.g., `wazuh-status`, `test-manager-connection`)
- Template names: lowercase with underscores
- Migrations: descriptive names (e.g., `0003_dual_connection_architecture`)

### JavaScript

- Vanilla JS (no frameworks)
- 2-space indentation
- Semicolons required
- `const`/`let` preferred over `var`
- Event listeners via `addEventListener`, not inline `onclick`

### CSS

- All custom CSS in `static/css/ariba-soc.css`
- Follow existing glassmorphism patterns (`background: rgba(...)`, `backdrop-filter: blur()`)
- Use CSS custom properties for theme colors
- Bootstrap 5 utility classes preferred over custom CSS where possible

### HTML Templates

- Extend `base.html` for all pages
- Use Django template tags (`{% block %}`, `{% url %}`, `{% static %}`)
- Role-gate UI elements with `{% if user.analystprofile.role in '...' %}`
- Always include CSRF token on POST forms

## Git Workflow

1. **Branch:** Create feature branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. **Commit:** Write descriptive commit messages:
   ```
   feat: add dual Wazuh connection architecture
   fix: resolve Indexer auth error in sync flow
   docs: update troubleshooting guide
   ```
3. **Push:** `git push origin feat/your-feature-name`
4. **PR:** Create pull request against `main` with:
   - Clear description of changes
   - Screenshots for UI changes
   - Test results

## Pull Request Checklist

- [ ] Code follows coding standards
- [ ] All existing tests pass (`python manage.py test`)
- [ ] New tests added for new functionality
- [ ] Migrations created if models changed (`python manage.py makemigrations`)
- [ ] No unnecessary whitespace changes
- [ ] Static files collected (`python manage.py collectstatic --noinput`)
- [ ] Documentation updated if applicable
- [ ] `.env` example updated if new variables added

## Testing

- Write tests for all new views, models, and services
- Tests should be in `tests.py` within the relevant app
- Use Django's `TestCase` class
- Mock external API calls in integration tests
- Run full test suite before submitting PR:
  ```bash
  python manage.py test
  ```

## Environment

- Use `python-decouple` for all configuration values
- Never hardcode credentials, URLs, or secrets
- Never commit `.env` to version control
- Update `.env.example` when adding new configuration variables
