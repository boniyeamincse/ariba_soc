# SEC-016: No real-time alert push (WebSocket)

**Severity:** Low  
**Priority:** P3  
**Category:** Missing Feature  
**Status:** Open  
**File:** `ariba_soc/`

## Current Problem
No real-time alert push. Analysts must refresh page to see new alerts.

## Expected Behavior
WebSocket push for new alerts.

## Affected Files
- `ariba_soc/config/settings.py`
- `ariba_soc/alerts/views.py`

## Suggested Fix
```bash
pip install channels
```
```python
# settings.py
INSTALLED_APPS += ['channels']
ASGI_APPLICATION = 'config.asgi.application'

# consumers.py
class AlertConsumer(WebsocketConsumer):
    def connect(self):
        self.room_group_name = 'alerts'
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name, self.channel_name
        )
        self.accept()
    
    def new_alert(self, event):
        self.send(text_data=json.dumps(event['data']))
```

## QA Verification
- Open dashboard in two browsers
- Trigger new alert → both browsers update
- No page refresh needed
