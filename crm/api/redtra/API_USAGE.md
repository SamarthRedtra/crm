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

## Properties

| Endpoint | Method | Auth | Notes |
| --- | --- | --- | --- |
| `/properties` | `GET` | Optional | Supports comprehensive filtering via query params: `listing_type`, `property_types`, price/bedroom/bathroom ranges, `amenities`, `location`, `area_id`, and `developer_id`. |
| `/properties/{property_id}` | `GET` | Optional | Returns full property detail. Guests only see active properties; authenticated users can view their own inactive drafts. Includes nested `developer` object when available. |
| `/properties` | `POST` | Agent / System Manager | Creates a property. Payload must include `title`, `listing_type`, `property_type`, `price`, `currency`. Optional `developer_id` links the property to a developer. Agent scope is enforced. |
| `/properties/{property_id}` | `PUT` | Agent / System Manager | Updates mutable fields. Pass `developer_id` to change developer association. |
| `/properties/{property_id}` | `DELETE` | Agent / System Manager | Soft deletes (sets status to `Inactive`). |
| `/properties/{property_id}/whatsapp-link` | `GET` | Agent / System Manager | Returns a WhatsApp deep link for the assigned agent. |

### Sample Create Payload

```json
{
  "title": "2 BHK Apartment in Al Jaddaf",
  "listing_type": "Sale",
  "property_type": "Apartment",
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
  "amenities": ["Pool", "Gym"]
}
```

The backend validates that the supplied `developer_id` exists and is `Active` before accepting the property.

## Developers

The new `Developer` DocType powers dedicated developer endpoints.

| Endpoint | Method | Auth | Notes |
| --- | --- | --- | --- |
| `/developers` | `GET` | Optional | Paginates developers. Supports `status`, `city`, and `search` filters. |
| `/developers/{developer_id}` | `GET` | Optional | Returns full company profile. Guests can access only active developers; authenticated System Managers can see inactive entries. |
| `/developers` | `POST` | System Manager | Creates a developer record. Requires at least `developer_name`. Optional metadata (contact info, address, logo) is accepted. |

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

## Areas

| Endpoint | Method | Auth | Notes |
| --- | --- | --- | --- |
| `/areas` | `GET` | Optional | Paginates areas. Filter with `city`. |
| `/areas/{area_id}` | `GET` | Optional | Returns area detail. |
| `/areas/{area_id}/properties` | `GET` | Agent / System Manager | Returns active properties within the area, constrained by agent scope when applicable. |

## Favorites & Appointments

These remain unchanged but require authentication:

- `/favorites` (`GET`, `POST`)
- `/favorites/{property_id}` (`DELETE`)
- `/appointments` (`GET`, `POST`)
- `/appointments/{appointment_id}` (`GET`, `PUT`, `DELETE`)

Refer to the OpenAPI document or Postman examples for payloads and expected responses.

## Error Handling

- `401 Unauthorized`: Missing/invalid token.
- `403 Forbidden`: Authenticated but lacks required roles (e.g., creating developers without System Manager role).
- `422 ValidationError`: Missing required fields or business rule violations (e.g., assigning an inactive developer).

## Testing Tips

- Always request a fresh token before sessions expire (default: 24 hours).
- Use the Postman collection to explore filters—many parameters are preconfigured but disabled; toggle them as needed.
- When integrating on the frontend, cache static datasets (areas, developers) and refresh periodically to minimize load.

For deeper schema details, inspect the OpenAPI spec or DocType definitions under `apps/crm/crm/fcrm/doctype/`.
