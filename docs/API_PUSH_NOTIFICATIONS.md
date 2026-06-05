# Push Notifications API (CRM Redtra)

## Overview

CRM push APIs for the **native Flutter app** (`com.example.darify`, Firebase project `darify-b9ff8`).

Implementation:

- `apps/crm/crm/api/redtra/push.py` — API handlers
- `apps/crm/crm/api/redtra/fcm.py` — direct Firebase Cloud Messaging (FCM HTTP v1)
- `apps/crm/crm/api/redtra/routes.py` — route registration

## Base URL

```text
https://darify.u.frappe.cloud/api/v1/notifications/push/...
```

## Authentication

All endpoints require JWT auth:

```http
Authorization: Bearer <JWT_TOKEN>
```

---

## Server setup (required once)

### Why not Frappe default relay?

The Flutter app uses **your own Firebase project** (`darify-b9ff8`).  
Frappe's default push relay uses the shared **`raven`** Firebase project. Tokens from `darify-b9ff8` will **not** deliver through the default relay.

CRM therefore supports **Darify Firebase** — server sends directly to FCM using your service account.

### Configure FCRM Settings

Desk → **FCRM Settings** → **Push Notifications**

| Field | Value |
|--------|--------|
| **Mobile Push Provider** | `Darify Firebase` |
| **Firebase Project ID** | `darify-b9ff8` |
| **Firebase Service Account Key** | Upload JSON key file from Firebase Console |

#### Get service account JSON

1. [Firebase Console](https://console.firebase.google.com/) → project **darify-b9ff8**
2. Project Settings → **Service accounts**
3. **Generate new private key** → download JSON
4. Upload the downloaded `.json` file in **Firebase Service Account Key** (Attach field) in FCRM Settings

> `google-services.json` in Flutter is the **client** config. The server needs the **service account key file** (different file).

#### Flutter app

Your `google-services.json` must stay on project `darify-b9ff8`:

```json
{
  "project_info": {
    "project_id": "darify-b9ff8"
  },
  "client": [{
    "android_client_info": {
      "package_name": "com.example.darify"
    }
  }]
}
```

---

## Endpoints

### 1) Register device token

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/v1/notifications/push/subscribe` |
| **Access** | Any authenticated JWT user |

#### Request body

```json
{
  "fcm_token": "fcm_device_token_here",
  "environment": "Mobile",
  "device_information": "{\"platform\":\"android\",\"app_version\":\"1.0.0\"}"
}
```

| Field | Required | Notes |
|--------|----------|--------|
| `fcm_token` | Yes | From `FirebaseMessaging.instance.getToken()` |
| `environment` | Yes | Use `Mobile` (also accepts `production`, `development`, `android`, `ios`) |
| `device_information` | No | JSON string |

Call **after login** and again on `onTokenRefresh`.

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
    "environment": "Mobile",
    "device_information": "{\"platform\":\"android\",\"app_version\":\"1.0.0\"}"
  }'
```

Token is stored in **Raven Push Token** for the logged-in user. With Darify Firebase enabled, it is **not** sent to Frappe relay.

---

### 2) Unregister device token

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/v1/notifications/push/unsubscribe` |
| **Access** | Any authenticated JWT user |

#### Request body

```json
{
  "fcm_token": "fcm_device_token_here"
}
```

#### Success response

```json
{
  "message": "Unsubscribed",
  "ok": true
}
```

---

### 3) Send push notification to one user

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/v1/notifications/push/send` |
| **Access** | `System Manager`, `Agency Admin`, `Agency Manager` |

#### Request body

```json
{
  "user_id": "agent@example.com",
  "title": "New Lead Assigned",
  "message": "A new lead has been assigned to you.",
  "data": {
    "type": "lead_assigned",
    "lead_id": "CRM-LEAD-0001"
  }
}
```

#### Success response (Darify Firebase)

```json
{
  "ok": true,
  "sent": true,
  "provider": "Darify Firebase",
  "token_count": 1,
  "sent_count": 1,
  "failed_count": 0,
  "message": "Push notification sent to 1 device(s)."
}
```

#### Failure response examples

No token registered:

```json
{
  "ok": false,
  "sent": false,
  "provider": "Darify Firebase",
  "token_count": 0,
  "sent_count": 0,
  "failed_count": 0,
  "message": "No registered FCM tokens found for this user."
}
```

FCM rejected token (stale token is auto-removed):

```json
{
  "ok": false,
  "sent": false,
  "provider": "Darify Firebase",
  "token_count": 1,
  "sent_count": 0,
  "failed_count": 1,
  "results": [
    {
      "token": "...",
      "success": false,
      "status_code": 404,
      "token_removed": true
    }
  ]
}
```

#### cURL

```bash
curl -X POST "https://darify.u.frappe.cloud/api/v1/notifications/push/send" \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "khansaahmed37@gmail.com",
    "title": "Staging test",
    "message": "Hello from Darify Firebase"
  }'
```

---

### 4) Send push notification to group/topic

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/v1/notifications/push/send-group` |
| **Access** | `System Manager`, `Agency Admin`, `Agency Manager` |

Still uses **Frappe Push Relay** topics (Raven). Not used for Darify Firebase direct send yet.

---

## Flutter integration checklist

1. Add `firebase_messaging` + `google-services.json` (`darify-b9ff8`)
2. Request notification permission (iOS + Android 13+)
3. After JWT login → `POST /notifications/push/subscribe` with `environment: "Mobile"`
4. Listen to `FirebaseMessaging.instance.onTokenRefresh` → re-subscribe
5. Handle foreground messages with `FirebaseMessaging.onMessage`
6. Test with app in **background** first (system tray)

---

## Where to verify delivery

| Check | Location |
|--------|----------|
| Token saved | Desk → **Raven Push Token** (user + `Mobile`) |
| Send result | API response `sent_count`, `failed_count`, `results` |
| FCM errors | Desk → **Error Log** (`CRM push send failed`) |
| Provider | FCRM Settings → **Mobile Push Provider** = `Darify Firebase` |

---

## Implementation mapping

| Route | Handler |
|--------|---------|
| `/notifications/push/subscribe` | `push.subscribe_push_token` |
| `/notifications/push/unsubscribe` | `push.unsubscribe_push_token` |
| `/notifications/push/send` | `push.send_push_notification` → `fcm.send_push_to_user` |
| `/notifications/push/send-group` | `push.send_group_push_notification` |

**Frappe Push Relay** is still available: set **Mobile Push Provider** to `Frappe Push Relay` in FCRM Settings (for Raven/web tokens only).
