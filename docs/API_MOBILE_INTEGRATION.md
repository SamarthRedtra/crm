# Google Sign-In — Mobile API Endpoints

Guide for **iOS/Android** developers integrating **Google login** with Darify CRM.

**Backend:** Frappe Social Login (`Social Login Key` → Google)  
**Implementation:** `apps/crm/crm/api/auth.py`, `frappe.integrations.oauth2_logins`

---

## Base URL

```text
https://<your-site-domain>
```

Example: `https://darify.u.frappe.cloud`

Frappe method APIs use `/api/method/...` (not `/api/v1/...`).

---

## Important: JWT vs session

| What Google login returns today | What mobile API needs |
|--------------------------------|------------------------|
| Frappe **session** (`sid` cookie) + browser redirect | **JWT** (`token`, `refresh_token`) from `POST /api/v1/auth/login` |

There is **no** `POST /api/v1/auth/google` (or similar) that accepts a Google `id_token` and returns JWT yet.  
Until that endpoint exists, use the **browser OAuth flow** below or email/password login for API access.

**Planned (not live):**

```http
POST /api/v1/auth/google
Content-Type: application/json

{ "id_token": "<Google ID token from native SDK>" }
```

Response should match `POST /api/v1/auth/login` (`token`, `refresh_token`, `user_id`, etc.).

---

## Endpoints

### 1. List OAuth providers (get Google `auth_url`)

Starts the Google OAuth flow. Call this before opening the Google sign-in UI.

| | |
|---|---|
| **Method** | `GET` or `POST` |
| **URL** | `{{base_url}}/api/method/crm.api.auth.oauth_providers` |
| **Auth** | None (guest) |
| **Content-Type** | Not required |

**Success response (200)**

```json
[
  {
    "name": "google",
    "provider_name": "Google",
    "auth_url": "https://accounts.google.com/o/oauth2/auth?client_id=...&redirect_uri=...&response_type=code&scope=...&state=...",
    "icon": "<img src='...' alt=Google>"
  }
]
```

| Field | Description |
|-------|-------------|
| `name` | Provider key in Frappe (usually `google`) |
| `provider_name` | Display name (`Google`) |
| `auth_url` | Full URL to open in browser / in-app web view |
| `icon` | HTML snippet for web UI (optional for mobile) |

**Mobile usage**

1. Call this endpoint on the login screen.
2. Find the item where `name` or `provider_name` is `Google`.
3. Open `auth_url` in:
   - iOS: `ASWebAuthenticationSession` or `SFSafariViewController`
   - Android: Chrome Custom Tab
4. User signs in with Google; Google redirects to the **callback URL** (endpoint 2).

**cURL**

```bash
curl -X GET "https://darify.u.frappe.cloud/api/method/crm.api.auth.oauth_providers"
```

**Notes**

- `auth_url` is built with `redirect_to=/crm` for the web app. For a custom mobile redirect, coordinate with backend/Ops (Social Login Key + Google Console redirect URIs).
- If the array is empty, Google social login is disabled or misconfigured in Frappe.

---

### 2. Google OAuth callback (complete login)

Called by **Google’s redirect** after the user approves access. Normally the **system browser / web view** hits this URL; the app intercepts the redirect if using a custom scheme or universal link.

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `{{base_url}}/api/method/frappe.integrations.oauth2_logins.login_via_google` |
| **Query params** | `code` (required), `state` (required) |
| **Auth** | None |

**Example**

```text
GET /api/method/frappe.integrations.oauth2_logins.login_via_google?code=4/0AeanS...&state=eyJzaXRlIjoiLi4uIn0=
```

**Default redirect URI** (must match Google Cloud Console and Frappe **Social Login Key → Google**):

```text
https://<your-site-domain>/api/method/frappe.integrations.oauth2_logins.login_via_google
```

**Success behavior**

- Creates or links a Frappe `User` from the Google profile (email required).
- Starts a Frappe **session** (sets `sid` / `user_id` cookies).
- **HTTP redirect** to `redirect_to` from OAuth `state` (web default: `/crm`).
- Does **not** return JSON with `token` / `refresh_token`.

**Errors**

- Invalid or missing `code` / `state` → HTML error page or 417.
- Signup disabled → 403 page.
- No email on Google account → error page.

**Handler chain**

`login_via_google` → `login_via_oauth2("google", code, state)` → Frappe `login_oauth_user`.

---

### 3. Login branding (optional, login screen)

| | |
|---|---|
| **Method** | `GET` or `POST` |
| **URL** | `{{base_url}}/api/method/crm.api.auth.public_brand` |
| **Auth** | None |

**Response**

```json
{
  "brand_name": "Darify",
  "brand_logo": "/files/logo.png"
}
```

Use for logo/title on the login screen alongside the Google button.

---

### 4. Exchange login token for session (optional, advanced)

Frappe can return a short-lived `login_token` only if OAuth is invoked with `generate_login_token=True` (not enabled for the default Google flow today). Documented for completeness.

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `{{base_url}}/api/method/frappe.www.login.login_via_token` |
| **Query** | `login_token=<token>` |

Establishes session from token (expires in ~120 seconds). **Not wired** to standard `login_via_google` in current CRM setup.

---

## Mobile integration flow (browser OAuth)

```text
┌─────────────┐     GET oauth_providers      ┌─────────────┐
│  Mobile App │ ───────────────────────────► │   Backend   │
│             │ ◄─────────────────────────── │             │
│             │      auth_url (Google)       └─────────────┘
│             │
│             │  Open auth_url in web view
│             ▼
┌─────────────┐     User signs in            ┌─────────────┐
│   Google    │ ───────────────────────────► │   Google    │
└─────────────┘                              └─────────────┘
       │
       │  Redirect with ?code=&state=
       ▼
┌─────────────┐     GET login_via_google     ┌─────────────┐
│  Web view   │ ───────────────────────────► │   Backend   │
│  (redirect) │ ◄── 302 + Set-Cookie sid    │  (session)  │
└─────────────┘                              └─────────────┘
```

**After callback**

- If you only need **Redtra JWT APIs**: you still need a backend bridge (planned `POST /auth/google`) or use **email/password** `POST /api/v1/auth/login`.
- If the app can use **session**: read `sid` from cookies on the callback URL (fragile on mobile) or ask backend to add JWT exchange.

---

## Google Cloud & Frappe configuration (Ops)

| Step | Where |
|------|--------|
| Create OAuth client | Google Cloud Console → APIs & Services → Credentials |
| iOS | Add iOS bundle ID (if using native SDK later) |
| Android | Add package name + SHA-1 (if using native SDK later) |
| Web redirect URI | `https://<domain>/api/method/frappe.integrations.oauth2_logins.login_via_google` |
| Enable Social Login | Frappe → **Social Login Key** → `google` |
| Client ID / Secret | Same as Google Cloud OAuth client |
| Enable Social Login | Checkbox on Social Login Key |

Site **Host Name** in site config must match the HTTPS domain used in redirect URIs.

---

## Endpoint summary

| # | Purpose | Method | Path |
|---|---------|--------|------|
| 1 | Get Google authorization URL | `GET` / `POST` | `/api/method/crm.api.auth.oauth_providers` |
| 2 | OAuth callback (code + state) | `GET` | `/api/method/frappe.integrations.oauth2_logins.login_via_google` |
| 3 | Login screen branding | `GET` / `POST` | `/api/method/crm.api.auth.public_brand` |
| — | **JWT from Google (native)** | `POST` | `/api/v1/auth/google` — **not implemented** |

---

## After Google login: API access

For all other mobile features (properties, push, profile), use JWT:

```http
POST /api/v1/auth/login
Authorization: (not required)

{ "email": "...", "password": "...", "remember_me": true }
```

Then:

```http
Authorization: Bearer <token>
```

See `API_PUSH_NOTIFICATIONS.md` and Postman **Authentication** folder for non-Google APIs.

---

## Contact backend before production if you need

- Native Google Sign-In with `id_token` → JWT
- Custom mobile redirect URI / deep link (`myapp://oauth/callback`)
- Returning `login_token` in OAuth response for session handoff

*Source: `crm.api.auth.oauth_providers`, `frappe.integrations.oauth2_logins.login_via_google`, Frappe `Social Login Key` (Google).*
