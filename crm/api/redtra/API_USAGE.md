# Redtra API Usage Guide

This guide summarizes the HTTP endpoints exposed under the Redtra API namespace so frontend engineers can discover, test, and integrate them quickly.

## Base URL & Versioning

- Base URL: `https://your-domain.com/api`
- Current OpenAPI document: `apps/crm/crm/api/redtra/openapi.yaml`
- Postman collection: `apps/crm/crm/api/redtra/postman_collection.json`

> Import the Postman collection and set the `base_url`, `token`, `property_id`, and `developer_id` variables to match your environment.

## Authentication

Redtra uses JWT bearer tokens for protected routes.

1. Register/Login via `/auth/register` or `/auth/login` (no authentication required).
2. On login success you will receive a `token` field.
3. Submit the token in subsequent requests using the `Authorization` header:
   ```http
   Authorization: Bearer <token>
   ```
4. When testing with curl:
   ```bash
   curl -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        https://your-domain.com/api/properties
   ```

### Guest Access

Some endpoints allow unauthenticated (guest) access for read-only data:

- `GET /properties` (listing)
- `GET /properties/{property_id}` (returns expanded detail, including developer info)
- `GET /areas`
- `GET /areas/{area_id}`
- `GET /developers`
- `GET /developers/{developer_id}` *(active developers only for guests)*

Any other endpoint requires a valid bearer token. System Manager permissions are required for certain actions (see below).

## Common Headers

- `Content-Type: application/json`
- `Authorization: Bearer <token>` (omit for guest endpoints)

## Authentication & Session

| Endpoint | Method | Auth | Notes |
| --- | --- | --- | --- |
| `/auth/register` | `POST` | None | Creates a new customer account. |
| `/auth/register` | `POST` | None | Include `is_agent=true` (and optional `agent_id`) to bind the signup to an Agent record. |
| `/auth/login` | `POST` | None | Exchanges credentials for a JWT token. |
| `/auth/forgot-password` | `POST` | Bearer | Logged-in users can rotate their password. |
| `/auth/logout` | `POST` | Bearer | Revokes the current JWT (blacklisted server-side). |

## User Profile

| Endpoint | Method | Auth | Notes |
| --- | --- | --- | --- |
| `/user/profile` | `GET` | Bearer | Returns customer details or the enriched agent dashboard payload. |
| `/user/profile` | `PUT` | Bearer | Updates contact info; agents can also update `about_me`, `profile_image`, DFD ID, and scheduling preferences. |

## Areas

| Endpoint | Method | Auth | Notes |
| --- | --- | --- | --- |
| `/areas` | `GET` | Optional | Paginated list of areas (filter by city). |
| `/areas/{area_id}` | `GET` | Optional | Returns the Area DocType record. |
| `/areas/{area_id}/properties` | `GET` | Agent / System Manager | Lists active properties in the area, respecting agent scoping rules. |

## Properties

| Endpoint | Method | Auth | Notes |
| --- | --- | --- | --- |
| `/properties` | `GET` | Optional | Supports comprehensive filtering via query params (see below). |
| `/properties/{property_id}` | `GET` | Optional | Returns full property detail. Guests only see active properties; authenticated users can view their own inactive drafts. Includes nested `developer` object when available. |
| `/properties` | `POST` | Agent / System Manager | Creates a property. Payload must include `title`, `listing_type`, `property_type`, `price`, `currency`. Optional `developer_id` links the property to a developer. Agent scope is enforced. |
| `/properties/{property_id}` | `PUT` | Agent / System Manager | Updates mutable fields. Pass `developer_id` / `property_category` to change associations. |
| `/properties/{property_id}` | `DELETE` | Agent / System Manager | Soft deletes (sets status to `Inactive`). |
| `/properties/{property_id}/whatsapp-link` | `GET` | Agent / System Manager | Returns a WhatsApp deep link for the assigned agent. |

### Sample Create Payload

```json
{
  "title": "2 BHK Apartment in Al Jaddaf",
  "listing_type": "Sale",
  "property_type": "Apartment",
  "property_category": "Residential",
  "price": 350000,
  "currency": "AED",
  "bedrooms": 2,
  "bathrooms": 2,
  "furnishing_status": "Furnished",
  "area_sqft": 1200,
  "area_id": "AREA-0001",
  "developer_id": "DEV-00001",
  "address_line1": "Creek Harbour",
  "city": "Dubai",
  "country": "United Arab Emirates",
  "amenities": ["Pool", "Gym"],
  "is_featured": true
}
```

The backend validates that the supplied `developer_id` exists and is `Active` before accepting the property.

### Key Property Filters

- `listing_type`, `property_types`, `property_category`
- Price, bedroom, bathroom, and area ranges (`min_*`, `max_*`)
- `amenities` (requires all specified values)
- `developer_id`, `area_id`, `agent`
- `is_featured` flag for curated listings
- Free-text `location` search covering area, city, state, country, address, and title

## Developers

The new `Developer` DocType powers dedicated developer endpoints.

| Endpoint | Method | Auth | Notes |
| --- | --- | --- | --- |
| `/developers` | `GET` | Optional | Paginates developers. Supports `status`, `city`, `search`, `include_property_stats`, `has_properties`, and `property_ids` filters. |
| `/developers/{developer_id}` | `GET` | Optional | Returns full company profile plus active property counts. Guests can access only active developers; authenticated System Managers can see inactive entries. |
| `/developers/{developer_id}/properties` | `GET` | Optional | Lists the active properties linked to a developer with pagination. |
| `/developers` | `POST` | System Manager | Creates a developer record. Requires at least `developer_name`. Optional metadata (contact info, address, logo) is accepted. |

- When `include_property_stats=true`, each developer summary contains `property_count` for active listings that match the current filters.
- Combine `property_ids` with the property import batch to quickly surface the developers represented on the home page.

### Sample Create Payload

```json
{
  "developer_name": "Sunrise Builders",
  "status": "Active",
  "email": "info@sunrise.example.com",
  "phone": "+971500000001",
  "website": "https://sunrise.example.com",
  "address_line1": "Downtown",
  "city": "Dubai",
  "country": "United Arab Emirates",
  "logo": "https://cdn.example.com/developers/sunrise-logo.png",
  "description": "Developer specializing in waterfront communities."
}
```

## Registration & Profile

- `POST /auth/register` now accepts an optional `agent_id` so invitation-driven signups can bind to pre-created Agent records.
- `GET /user/profile` returns richer agent analytics:
  - `agent_profile` (status, about me, profile image, max daily appointments)
  - `appointments_today` (scheduled slots for the current day)
  - `properties` (recent active listings for the agent)
  - `lead_stats` (totals, today’s leads, last-month comparison, trend ratio)
- `PUT /user/profile` accepts `about_me`, `profile_image`, and `max_daily_appointments` alongside the existing contact fields; agent and user records stay in sync.

### Agent Registration Example

```json
{
  "full_name": "Fatima Ali",
  "email": "fatima.agent@example.com",
  "password": "StrongPassword123!",
  "is_agent": true,
  "agent_id": "AGENT-0005",
  "phone": "+971500000010",
  "whatsapp_number": "+971500000011",
  "bio": "Specialist in luxury villas across Dubai."
}
```

If `agent_id` is omitted, the API creates a fresh Agent record for the new user. When it is supplied, the backend looks for an Agent whose `dfd_registration_id` matches that value (and links it to the signing-up user). The legacy Agent name is no longer required for this mapping.

## Favorites

| Endpoint | Method | Auth | Notes |
| --- | --- | --- | --- |
| `/favorites` | `GET` | Bearer | Lists the authenticated user’s saved properties. |
| `/favorites` | `POST` | Bearer | Adds a property to the favorites list (`property_id` required). |
| `/favorites/{property_id}` | `DELETE` | Bearer | Removes a property from favorites. |

## Appointments

| Endpoint | Method | Auth | Notes |
| --- | --- | --- | --- |
| `/appointments` | `GET` | Bearer | Paginated list of appointments scoped to the current user. |
| `/appointments` | `POST` | Bearer | Creates an appointment for a property. |
| `/appointments/{appointment_id}` | `GET` | Bearer | Retrieves appointment details. |
| `/appointments/{appointment_id}` | `PUT` | Bearer | Updates timing or notes for an appointment. |
| `/appointments/{appointment_id}` | `DELETE` | Bearer | Cancels an appointment. |

Every confirmed booking automatically creates/maintains a linked `Event` (`calendar_event`) on the property, so schedule changes and cancellations stay visible in the CRM calendar.

## Notifications

| Endpoint | Method | Auth | Notes |
| --- | --- | --- | --- |
| `/notifications` | `GET` | Bearer | Paginated notifications; use `unread_only=true` to focus on pending items. |
| `/notifications/mark-read` | `POST` | Bearer | Marks specific (or all) notifications as read. |

Refer to the OpenAPI document or Postman examples for payload structures and expected responses.

## Error Handling

- `401 Unauthorized`: Missing/invalid token.
- `403 Forbidden`: Authenticated but lacks required roles (e.g., creating developers without System Manager role).
- `422 ValidationError`: Missing required fields or business rule violations (e.g., assigning an inactive developer).

## Testing Tips

- Always request a fresh token before sessions expire (default: 24 hours).
- Use the Postman collection to explore filters—many parameters are preconfigured but disabled; toggle them as needed.
- When integrating on the frontend, cache static datasets (areas, developers) and refresh periodically to minimize load.

For deeper schema details, inspect the OpenAPI spec or DocType definitions under `apps/crm/crm/fcrm/doctype/`.
