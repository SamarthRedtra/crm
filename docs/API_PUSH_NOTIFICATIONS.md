# Push Notifications API (CRM Redtra)

## Overview

This document covers CRM wrapper APIs implemented in:

- `apps/crm/crm/api/redtra/push.py`
- Route registrations in `apps/crm/crm/api/redtra/routes.py`

These endpoints expose token registration and push sending capabilities through CRM APIs.

## Base URL

All routes below are registered in Frappe API v1:

- `https://darify.u.frappe.cloud/api/v1/notifications/push/...`

Example:

- `https://darify.u.frappe.cloud/api/v1/notifications/push/subscribe`

## Authentication

All endpoints require JWT auth via `Authorization: Bearer <token>`.

## Endpoints

### 1) Register device token

- **Method:** `POST`
- **Path:** `/api/v1/notifications/push/subscribe`
- **Handler:** `push.subscribe_push_token`
- **Access:** Any authenticated JWT user

#### Request body

```json
{
  "fcm_token": "fcm_device_token_here",
  "environment": "production",
  "device_information": "{\"platform\":\"ios\",\"app_version\":\"1.0.0\"}"
}
```

Notes:

- `fcm_token` is required.
- `environment` is required (example: `production`, `development`).
- `device_information` is optional.

#### Success response

```json
{
  "message": "Subscribed",
  "ok": true
}
```

#### cURL

```bash
curl -X POST "https://darify.u.frappe.cloud/api/v1/notifications/push/subscribe" \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "fcm_token": "fcm_device_token_here",
    "environment": "production",
    "device_information": "{\"platform\":\"android\",\"app_version\":\"1.0.0\"}"
  }'
```

---

### 2) Unregister device token

- **Method:** `POST`
- **Path:** `/api/v1/notifications/push/unsubscribe`
- **Handler:** `push.unsubscribe_push_token`
- **Access:** Any authenticated JWT user

#### Request body

```json
{
  "fcm_token": "fcm_device_token_here"
}
```

Notes:

- `fcm_token` is required.

#### Success response

```json
{
  "message": "Unsubscribed",
  "ok": true
}
```

#### cURL

```bash
curl -X POST "https://darify.u.frappe.cloud/api/v1/notifications/push/unsubscribe" \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "fcm_token": "fcm_device_token_here"
  }'
```

---

### 3) Send push notification to one user

- **Method:** `POST`
- **Path:** `/api/v1/notifications/push/send`
- **Handler:** `push.send_push_notification`
- **Access roles:** `System Manager`, `Agency Admin`, `Agency Manager`

#### Request body

```json
{
  "user_id": "agent@example.com",
  "title": "New Lead Assigned",
  "message": "A new lead has been assigned to you.",
  "data": {
    "type": "lead_assigned",
    "lead_id": "CRM-LEAD-0001",
    "channel_id": "CHANNEL-0001"
  },
  "user_image_path": "/files/avatar.png"
}
```

Notes:

- `user_id`, `title`, and `message` are required.
- `data` is optional and defaults to `{}`.
- `user_image_path` is optional.

#### Success response

```json
{
  "message": "Push notification sent.",
  "ok": true
}
```

#### cURL

```bash
curl -X POST "https://darify.u.frappe.cloud/api/v1/notifications/push/send" \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "agent@example.com",
    "title": "New Lead Assigned",
    "message": "A new lead has been assigned to you.",
    "data": {
      "type": "lead_assigned",
      "lead_id": "CRM-LEAD-0001"
    }
  }'
```

---

### 4) Send push notification to group/topic

- **Method:** `POST`
- **Path:** `/api/v1/notifications/push/send-group`
- **Handler:** `push.send_group_push_notification`
- **Access roles:** `System Manager`, `Agency Admin`, `Agency Manager`

#### Request body

```json
{
  "group_id": "AGENCY-CHANNEL-001",
  "title": "Daily Update",
  "message": "5 new properties are live today.",
  "data": {
    "type": "daily_summary",
    "agency_id": "AGY-0001"
  },
  "user_image_path": "/files/agency-logo.png"
}
```

Notes:

- `group_id`, `title`, and `message` are required.
- `group_id` maps to Raven topic/channel id (`send_notification_to_topic(channel_id=group_id, ...)`).
- `data` is optional and defaults to `{}`.
- `user_image_path` is optional.

#### Success response

```json
{
  "message": "Group push notification sent.",
  "ok": true
}
```

#### cURL

```bash
curl -X POST "https://darify.u.frappe.cloud/api/v1/notifications/push/send-group" \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "AGENCY-CHANNEL-001",
    "title": "Daily Update",
    "message": "5 new properties are live today.",
    "data": {
      "type": "daily_summary",
      "agency_id": "AGY-0001"
    }
  }'
```

## Error behavior

- Missing required fields return validation errors from `utils.get_request_json`.
- Unauthorized/invalid JWT returns auth errors from `utils.require_jwt`.
- Role mismatch on send endpoints returns permission errors.
- Unsubscribe with unknown token can return Raven-side `"FCM token not found"` error.

## Implementation mapping

- Route definitions: `apps/crm/crm/api/redtra/routes.py`
  - `/notifications/push/subscribe` -> `push.subscribe_push_token`
  - `/notifications/push/unsubscribe` -> `push.unsubscribe_push_token`
  - `/notifications/push/send` -> `push.send_push_notification`
  - `/notifications/push/send-group` -> `push.send_group_push_notification`
- API handlers: `apps/crm/crm/api/redtra/push.py`
- Underlying token mapping APIs: `raven.api.notification.subscribe` and `raven.api.notification.unsubscribe`
- Underlying push send APIs: `raven.notification.send_notification_to_user` and `raven.notification.send_notification_to_topic`
