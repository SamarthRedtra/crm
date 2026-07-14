# Darify Firebase Push — Setup & Troubleshooting Guide

Shareable guide for backend, mobile, and DevOps teams setting up **Darify Firebase** push notifications for the native Flutter app.

**App:** `com.example.darify`  
**Firebase project:** `darify-b9ff8`  
**Backend:** Frappe CRM (Redtra API)

---

## Quick summary

| What | Where |
|------|--------|
| Flutter app config | `google-services.json` (project `darify-b9ff8`) |
| Server config | Frappe → **FCRM Settings** → **Push Notifications** |
| Server credential | **Service account JSON** from Firebase Console (not `google-services.json`) |
| Device tokens | DocType: **Raven Push Token** |
| Send API | `POST /api/v1/notifications/push/send` |

---

## Architecture

```text
Flutter App (darify-b9ff8)
    │
    ├─ google-services.json          → client SDK config
    ├─ FirebaseMessaging.getToken()  → FCM device token
    │
    └─ POST /notifications/push/subscribe (JWT)
              │
              ▼
       Raven Push Token (DB)
              │
              ▼
       POST /notifications/push/send (JWT + admin role)
              │
              ▼
       FCM HTTP v1 API (darify-b9ff8)
              │
              ▼
       Device notification
```

**Why not Frappe default relay?**  
Frappe's built-in push relay uses the shared `raven` Firebase project. Tokens from `darify-b9ff8` will not deliver through that relay. CRM sends directly to your Firebase project using a service account.

---

## Step 1 — Firebase project setup

### 1.1 Flutter app (`google-services.json`)

1. Firebase Console → project **`darify-b9ff8`**
2. Add Android app with package `com.example.darify`
3. Download `google-services.json`
4. Place in Flutter project (Android)

Expected shape:

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

> **Do not upload this file to FCRM Settings.** It is for the mobile app only.

---

### 1.2 Server service account key (required)

1. Firebase Console → project **`darify-b9ff8`**
2. **Project Settings** → **Service accounts**
3. Click **Generate new private key** → download JSON

A valid service account key looks like:

```json
{
  "type": "service_account",
  "project_id": "darify-b9ff8",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-xxxxx@darify-b9ff8.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
```

**Required fields:** `type`, `project_id`, `private_key`, `client_email`, `token_uri`

---

### 1.3 Google Cloud IAM permissions

In [Google Cloud Console](https://console.cloud.google.com/) → project **`darify-b9ff8`**:

1. **IAM & Admin** → **IAM**
2. Find the service account email from the JSON (`client_email`)
3. Add role: **Firebase Cloud Messaging Admin** (or **Firebase Admin**)

Also enable the API:

1. **APIs & Services** → **Library**
2. Search **Firebase Cloud Messaging API**
3. Click **Enable**

Direct link:

```text
https://console.cloud.google.com/apis/library/fcm.googleapis.com?project=darify-b9ff8
```

Wait 1–2 minutes after IAM changes before testing.

---

## Step 2 — Frappe / FCRM Settings

Desk → **FCRM Settings** → **Push Notifications**

| Field | Value |
|--------|--------|
| **Mobile Push Provider** | `Darify Firebase` |
| **Firebase Project ID** | `darify-b9ff8` |
| **Firebase Service Account Key** | Upload the service account JSON from Step 1.2 |
| **Firebase Request Timeout (Seconds)** | `15` (default is fine) |

Click **Save**.

### Verification checklist

| Check | Expected |
|--------|----------|
| `project_id` in uploaded JSON | `darify-b9ff8` |
| `client_email` ends with | `@darify-b9ff8.iam.gserviceaccount.com` |
| Flutter `google-services.json` project | `darify-b9ff8` |
| IAM role on service account | Firebase Cloud Messaging Admin |
| FCM API | Enabled |

---

## Step 3 — Get JWT for API testing

Push APIs require a JWT bearer token. The token is **not** stored in any DocType — get it from the login API.

```bash
curl -X POST "https://<your-site>/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "your-password",
    "remember_me": true
  }'
```

Response:

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "...",
  "user_id": "admin@example.com"
}
```

Use in all requests:

```http
Authorization: Bearer <token>
```

**Postman:** Import `apps/crm/crm/api/redtra/postman_collection.json` → run **Authentication → Login** → token is saved as `{{token}}`.

---

## Step 4 — API endpoints

Base URL:

```text
https://<your-site>/api/v1/notifications/push/...
```

### Register device token

```http
POST /api/v1/notifications/push/subscribe
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "fcm_token": "<from FirebaseMessaging.getToken()>",
  "environment": "Mobile",
  "device_information": "{\"platform\":\"android\",\"app_version\":\"1.0.0\"}"
}
```

Call after login and on `onTokenRefresh`.

### Send push to one user

Requires role: `System Manager`, `Agency Admin`, or `Agency Manager`.

```http
POST /api/v1/notifications/push/send
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "user_id": "user@example.com",
  "title": "Test",
  "message": "Hello from Darify Firebase",
  "data": {
    "type": "test"
  }
}
```

### Success response

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

### Unregister device token

```http
POST /api/v1/notifications/push/unsubscribe
Authorization: Bearer <JWT>

{
  "fcm_token": "<token>"
}
```

---

## Step 5 — Flutter integration checklist

1. Add `firebase_messaging` + `google-services.json` (`darify-b9ff8`)
2. Request notification permission (iOS + Android 13+)
3. User logs in → get JWT from `POST /api/auth/login`
4. `POST /notifications/push/subscribe` with `environment: "Mobile"`
5. Listen to `FirebaseMessaging.instance.onTokenRefresh` → re-subscribe
6. Handle foreground: `FirebaseMessaging.onMessage`
7. Test with app in **background** first (system tray)

---

## Troubleshooting

### Error 1 — `missing fields token_uri`

```text
google.auth.exceptions.MalformedError: Service account info was not in the expected format, missing fields token_uri.
```

**Cause:** Wrong JSON uploaded to FCRM Settings.

| Wrong | Correct |
|--------|---------|
| `google-services.json` | Service account key JSON |
| Manually pasted `private_key` into `google-services.json` | Full key from Firebase Console |
| Has `project_info` + `client` keys | Has `type`, `token_uri`, `client_email`, `private_key` |

**Fix:**

1. Firebase Console → `darify-b9ff8` → Service accounts → **Generate new private key**
2. Upload that file to **FCRM Settings → Firebase Service Account Key**
3. Save

---

### Error 2 — `403 PERMISSION_DENIED` / `cloudmessaging.messages.create`

```json
{
  "status_code": 403,
  "response": {
    "error": {
      "message": "Permission 'cloudmessaging.messages.create' denied on resource 'projects/darify-b9ff8'"
    }
  }
}
```

**Cause:** Service account cannot send FCM messages on `darify-b9ff8`.

Common reasons:

1. Service account is from a **different project** (e.g. `@darify-portal.iam.gserviceaccount.com`)
2. Missing IAM role on the service account
3. Firebase Cloud Messaging API not enabled

**Fix:**

1. Regenerate key from project **`darify-b9ff8`** (not another project)
2. Confirm `client_email` ends with `@darify-b9ff8.iam.gserviceaccount.com`
3. Google Cloud IAM → add **Firebase Cloud Messaging Admin** to that email
4. Enable **Firebase Cloud Messaging API**
5. Re-upload key in FCRM Settings → Save → wait 1–2 min → retry

---

### Error 3 — `No registered FCM tokens found for this user`

```json
{
  "ok": false,
  "token_count": 0,
  "message": "No registered FCM tokens found for this user."
}
```

**Cause:** User has not subscribed, or `user_id` in send request does not match the logged-in user who subscribed.

**Fix:**

1. App calls `POST /notifications/push/subscribe` after login
2. Verify in Desk → **Raven Push Token** (filter by user)
3. Use the same email as `user_id` in the send request

---

### Error 4 — `404` / token removed

```json
{
  "success": false,
  "status_code": 404,
  "token_removed": true
}
```

**Cause:** FCM token is stale (app reinstalled, token refreshed, uninstalled).

**Fix:** App re-subscribes on launch and `onTokenRefresh`. Stale tokens are auto-deleted from **Raven Push Token**.

---

### Error 5 — Push send works but device does not show notification

| Check | Action |
|--------|--------|
| App in foreground | Use `onMessage` handler; system tray may not show banner |
| Android 13+ | Notification permission granted |
| iOS | APNs configured in Firebase + correct provisioning |
| Token project mismatch | App `google-services.json` must be `darify-b9ff8` |
| Test in background first | Put app in background, then send |

---

## Where to verify in Frappe Desk

| What | Where |
|------|--------|
| Device FCM tokens | **Raven Push Token** (user + environment `Mobile`) |
| Push provider config | **FCRM Settings** → Push Notifications |
| API / server errors | **Error Log** |
| Refresh token records (hashed only) | **Redtra Refresh Token** |

> JWT access tokens are **not** stored in Desk. Get them only from `POST /api/auth/login`.

---

## Security notes

- **Never** commit service account JSON to git or share in chat
- **Never** use `google-services.json` as the server credential
- If a private key is exposed, **revoke and regenerate** in Firebase Console immediately
- Rotate service account keys periodically

---

## File reference

| File | Purpose |
|------|---------|
| `google-services.json` | Flutter/Android client — stays in mobile project |
| Service account `*.json` | Server FCM auth — upload to FCRM Settings only |
| `apps/crm/docs/API_PUSH_NOTIFICATIONS.md` | API endpoint reference |
| `apps/crm/crm/api/redtra/postman_collection.json` | Postman collection for testing |
| `apps/crm/crm/api/redtra/fcm.py` | FCM send implementation |

---

## Contact / handoff checklist

Before marking push as production-ready:

- [ ] Service account from `darify-b9ff8` uploaded to FCRM Settings
- [ ] `client_email` domain matches `darify-b9ff8`
- [ ] IAM role: Firebase Cloud Messaging Admin
- [ ] FCM API enabled
- [ ] Flutter uses `google-services.json` for `darify-b9ff8`
- [ ] Subscribe API called after login
- [ ] Send API returns `sent_count >= 1`
- [ ] Notification received on physical device (background test)
- [ ] Stale tokens cleaned up automatically on 404

---

*Last updated: June 2026 — Darify CRM Redtra push (FCM HTTP v1)*
