# Wazuh API Setup Guide

## Pre-requisites
You must have a running Wazuh Manager instance with API access enabled (default port 55000).

## 1. Gather Wazuh Credentials
Obtain the API Username and Password for your Wazuh instance. It is recommended to create a dedicated read-only API user for Ariba SOC.

## 2. Configure Ariba SOC
1. Log into Ariba SOC as an Administrator.
2. Navigate to `Settings -> Wazuh API Settings`.
3. Enter the API URL (e.g., `https://wazuh-manager.local:55000`).
4. Enter the Username and Password.
5. Set the **Sync Interval** (in minutes) to define how often Ariba SOC fetches new alerts.
6. Toggle **Enable Integration**.
7. Click **Save Configuration**.

## 3. Verification
Navigate to the **Wazuh** tab in the main top navbar.
Click **Force Sync** to test the connection. Check the "Recent Sync Activity" logs for a `Success` message.
