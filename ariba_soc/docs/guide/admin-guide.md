# Administrator Guide

## Overview
As an Administrator, you have full control over the platform's configuration, user management, and core logic via the **Settings Dashboard**.

## 1. User Management
Navigate to `Settings -> User Management`.
- Create new users, assign roles (e.g., `SOC_L1`, `SOC_MGR`), and set their team.
- Users can be deactivated instantly via the toggle button, which revokes their access without deleting their historical audit trails.

## 2. Role & Permission Matrix
Navigate to `Settings -> Role & Permission`.
- Define exactly what each role can do (e.g., `can_escalate_alert`, `can_export_reports`).
- Only Administrators can alter this matrix.

## 3. System Settings
For global platform configurations (e.g., Company Name, Global Timezone), utilize the `System Settings` panel.

## 4. Django Admin
For low-level database modifications, you can access the core Django Admin panel via the link at the bottom of the Settings sidebar. Use this with caution.
