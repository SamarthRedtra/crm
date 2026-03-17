# CRM API & Frontend Changes – March 2026

## Summary

This note covers the latest updates to the CRM app: Switch to CRM behavior, API changes, and a new Get SID endpoint.

---

## 1. Switch to CRM – Dashboard as Default

**Before:** Visiting `/crm?sid=xxx` redirected to the Leads screen.  
**After:** When no default view is configured, users are redirected to the **Dashboard** instead of Leads.

---

## 2. Switch to CRM After Logout – No More Server Error

**Before:** After logout, clicking "Switch to CRM" with an expired SID caused a server error.  
**After:** Invalid or expired SID redirects to the **login page** with `redirect-to=/crm`, so users can log in again.

---

## 3. Login API – `is_agent` Field

**Change:** The login response now includes `is_agent` (boolean).

**Example response:**
```json
{
  "token": "...",
  "refresh_token": "...",
  "sid": "...",
  "user_id": "user@example.com",
  "full_name": "John Doe",
  "remember_me": true,
  "token_expires_in_hours": 24,
  "is_agent": true
}
```

---

## 4. Agencies List API – Listing Counts

**Change:** Each agency in the list now includes listing counts.

**New fields per agency:**
- `active_listings` – Total active listings
- `sale_listings` – Buy listings count
- `rent_listings` – Rent listings count

---

## 5. Transactions API – Public Access for Agent Profile

**List Transactions:**
- **Guest access:** No auth required when the `agent` query param is provided (agent ID or BRN).
- **Authenticated:** When `agent` is not provided, auth is required (scoped to the logged-in agent or System Manager).
- **URL:** `GET /api/transactions?agent={agent_id}` (no auth needed)

**Get Transaction:**
- **Change:** Auth removed. Anyone can view transaction details.
- **URL:** `GET /api/transactions/{transaction_id}` (no auth needed)

---

## 6. Agent Rating in Property & Agent Detail APIs

**Property Detail API:** The `agent` object now includes a `ratings` field with:
- `average_overall_rating`
- `average_agent_rating`
- `average_property_rating`
- `total_reviews`
- `recent_reviews`

**Agent Detail API:** Already included ratings; no change.

---

## 7. New API – Get SID

**Purpose:** Get a fresh SID when the JWT is valid but the session (SID) has expired (e.g. after logout or timeout).

**Endpoint:** `GET /api/auth/get-sid`  
**Auth:** Bearer JWT required  
**Response:** `{"sid": "new_session_id"}`

**Flow:**
1. Call `GET /api/auth/get-sid` with `Authorization: Bearer {token}`.
2. Use the returned `sid` in the Switch to CRM URL: `/crm?sid={sid}`.

---

## Postman Collection Updates

The Postman collection has been updated with:
- New **Get SID** request under Authentication
- `sid` collection variable (auto-set from Login and Get SID)
- **List Transactions** – `agent` query param and no-auth option
- **Get Transaction** – no auth
- **List Agencies** – description of new count fields
- Corrected API paths (`/api/transactions` instead of `/api/v1/transactions`)

Import the updated collection from: `apps/crm/crm/api/redtra/postman_collection.json`
