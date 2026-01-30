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

- `GET /properties` (listing) - **Now includes amenities and gallery in response**
- `GET /properties/{property_id}` (returns expanded detail, including developer info, amenities, and gallery)
- `GET /areas`
- `GET /areas/{area_id}`
- `GET /developers`
- `GET /developers/{developer_id}` *(active developers only for guests)*
- `GET /agents` - **NEW: List agents (public)**
- `GET /agents/{agent_id}` - **NEW: Get agent details (public)**
- `GET /agents/{agent_id}/available-slots` - **NEW: Get agent availability slots (public)**
- `GET /agencies/{agency_id}/profile` - **NEW: Get full agency profile (public)**
- `GET /agencies/{agency_id}/agents` - **NEW: List agency agents (public)**
- `GET /agencies/{agency_id}/analytics` - **NEW: Agency analytics (public)**

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
  "listing_type": "Buy",
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
  "is_featured": true,
  "featured_until": "2026-02-01 12:00:00"
}
```

The backend validates that the supplied `developer_id` exists and is `Active` before accepting the property.

### Key Property Filters

- `listing_type`, `property_types`, `property_category`
- Price, bedroom, bathroom, and area ranges (`min_*`, `max_*`)
- `amenities` (requires all specified values)
- `developer_id`, `area_id`, `agent`
- `is_featured` flag for curated listings
- `featured_until` timestamp for featured listings (auto-expires)
- `furnished` / `is_furnished` booleans filter fully furnished homes (false excludes them).
- `min_area_sq_ft` and `max_area_sq_ft` are aliases for square-foot filtering alongside `min_area`/`max_area`.
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
- `remember_me` flag lets the frontend remember a customer or agent during registration (mirrors the new checkbox field).
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

## Agents

| Endpoint | Method | Auth | Notes |
| --- | --- | --- | --- |
| `/agents` | `GET` | None | Public endpoint to list verified agents. Supports `page`, `page_size`, `status`, and `search` filters. |
| `/agents/{agent_id}` | `GET` | None | Public endpoint to get agent details including availability slots, max appointment minutes, and properties. |
| `/agents/{agent_id}/available-slots` | `GET` | None | **NEW:** Public endpoint to get available appointment slots for an agent. Supports `start_date` and `end_date` query parameters. Returns only slots that are not already booked. |
| `/agents/availability` | `POST` | Agent | **NEW:** Update agent's availability schedule and max appointment minutes. Requires authentication as the agent. |

## Agencies

| Endpoint | Method | Auth | Notes |
| --- | --- | --- | --- |
| `/agencies/{agency_id}/profile` | `GET` | None | Returns full agency profile with metadata. |
| `/agencies/{agency_id}/agents` | `GET` | None | Lists agents associated with the agency. |
| `/agencies/{agency_id}/analytics` | `GET` | None | Returns totals for leads, sales, rent, and active listings. |

### Agent Availability Slots

Agents can define their weekly availability schedule:

```json
{
  "max_appointment_minutes": 30,
  "availability_slots": [
    {
      "day_of_week": "Monday",
      "start_time": "09:00:00",
      "end_time": "17:00:00"
    },
    {
      "day_of_week": "Tuesday",
      "start_time": "09:00:00",
      "end_time": "17:00:00"
    }
  ]
}
```

- `day_of_week`: Must be Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, or Sunday
- `start_time` / `end_time`: Time format "HH:MM:SS" or "HH:MM"
- `max_appointment_minutes`: Duration for each appointment slot (default: 30)

## Appointments

| Endpoint | Method | Auth | Notes |
| --- | --- | --- | --- |
| `/appointments` | `GET` | Bearer | Paginated list of appointments scoped to the current user. |
| `/appointments` | `POST` | Bearer | Creates an appointment for a property. **Validates against agent availability slots and appointment duration.** |
| `/appointments/{appointment_id}` | `GET` | Bearer | Retrieves appointment details. |
| `/appointments/{appointment_id}` | `PUT` | Bearer | Updates timing or notes for an appointment. |
| `/appointments/{appointment_id}` | `DELETE` | Bearer | Cancels an appointment. |
| `/agents/{agent_id}/available-slots` | `GET` | None | **NEW:** Get available appointment slots for an agent (public endpoint). |

Every confirmed booking:
- Validates against agent's availability schedule
- Checks for appointment duration match (`max_appointment_minutes`)
- Validates slot is not already booked
- Automatically creates notifications for both customer and agent
- Creates/maintains a linked `Event` (`calendar_event`) on the property, so schedule changes and cancellations stay visible in the CRM calendar

## Notifications

| Endpoint | Method | Auth | Notes |
| --- | --- | --- | --- |
| `/notifications` | `GET` | Bearer | Paginated notifications; use `unread_only=true` to focus on pending items. **Returns appointment booking notifications.** |
| `/notifications/mark-read` | `POST` | Bearer | Marks specific (or all) notifications as read. |

**Notification Types:**
- **Appointment Booked:** Both customer and agent receive notifications when an appointment is created
- Customer receives: Confirmation notification with appointment details
- Agent receives: New appointment notification with customer details

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

## New Features (Latest Updates)

### 1. Property List/Detail Enhancement
- Property list API now includes `amenities` and `gallery` arrays in the response
- Property detail API already included these; now consistent across endpoints

### 2. Agent Availability Management
- Agents can define weekly availability slots via `POST /api/agents/availability`
- Each slot defines: day of week, start time, end time
- Agents set `max_appointment_minutes` to define appointment duration
- Availability is agent-specific (stored in child table)

### 3. Smart Appointment Booking
- `GET /api/agents/{agent_id}/available-slots` returns only available (unbooked) slots
- Appointment creation validates against agent's availability schedule
- Prevents double-booking and enforces appointment duration rules

### 4. Automatic Notifications
- Appointment booking automatically creates notifications for customer and agent
- Notifications appear in `GET /api/notifications` endpoint
- Includes appointment details and reference links

### 5. Agent Verification Control
- Controlled by `mandate_agent_verification` setting in Property Settings
- When enabled: Only verified agents can be accessed/booked
- When disabled: All agents are accessible regardless of verification status

---

## Developer Guide

For a comprehensive developer guide with code examples, workflows, and best practices, see:
- **Developer Guide:** `apps/crm/crm/api/redtra/DEVELOPER_GUIDE.md`
- **Sequence Diagrams:** `apps/crm/crm/api/redtra/SEQUENCE_DIAGRAMS.md` (Visual workflow diagrams)
