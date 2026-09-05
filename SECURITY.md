# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability within Ariba SOC, please send an email to **boniyeamin.cse1@gmail.com**. All security vulnerabilities will be promptly addressed.

**Please do NOT report security vulnerabilities through public GitHub issues.**

## Disclosure Policy

When the security team receives a security bug report, they will assign it to a primary handler. This person will coordinate the fix and release process, involving the following steps:

1. Confirm the problem and determine the affected versions.
2. Audit code to find any potential similar problems.
3. Prepare fixes for all releases still under maintenance.
4. Release new security versions.

## Security Update Process

Security updates will be released as patch versions. For example, if the current version is 1.2.3, a security fix would be released as 1.2.4.

## Security Considerations

### Authentication & Authorization
- All passwords are hashed using Django's PBKDF2 algorithm
- Session cookies areSecure/HttpOnly in production
- CSRF protection is enabled on all forms
- Role-based access control (RBAC) is enforced

### Data Protection
- Sensitive data (Wazuh API credentials) is encrypted at rest
- Database connections use SSL in production
- All API traffic should be over HTTPS

### Infrastructure
- Docker containers run as non-root users
- SSL certificates are generated for internal services
- Network segmentation via Docker networks

## Known Security Gaps

See `ariba_soc/issues/01-function-security/` for documented security issues and their remediation status.
