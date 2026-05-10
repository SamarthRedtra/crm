# Lead sync API (CRM Lead + Property)

## Overview

External systems can **create or update** a **CRM Lead** and optionally link it to a **Property** using:

`POST /api/method/crm.api.lead_sync_api.sync_lead`

Authentication: same as other CRM APIs (logged-in user session cookie, or `Authorization: Bearer <token>` if your site uses token auth).

Allowed Frappe roles (same as other CRM mutations): **System Manager**, **Sales Manager**, **Agency Admin**, **Agency Manager**, **Sales User**.

## Field on CRM Lead

The Property is stored on **`custom_property`** (label **Property**, Link → **Property**). This field is part of the `CRM Lead` doctype (`custom_property` in `crm_lead.json`). After pulling the latest app code, run:

```bash
bench --site <site> migrate
```

## Request body (JSON)

| Key | Required | Description |
|-----|----------|-------------|
| `lead` | Yes* | Object with CRM Lead fields (see below) or JSON string of that object. |
| `property_name` | No | Property document name (e.g. `PROP-2026-00001`). Can also be sent as `lead.custom_property` or `lead.property`. |
| `lead.name` | For update | Existing CRM Lead ID to update. |

\*For **create**, `lead` must include **`first_name`** and **`email`**.

### Allowed keys in `lead`

`first_name`, `last_name`, `email`, `mobile_no`, `phone`, `job_title`, `status`, `source`, `agency`, `agent_id`, `territory`, `website`, `no_of_employees`, `annual_revenue`, and `name` (for updates). Other keys are ignored.

## Examples

### Create lead with property

```http
POST /api/method/crm.api.lead_sync_api.sync_lead
Content-Type: application/json
```

```json
{
  "property_name": "PROP-2026-00001",
  "lead": {
    "first_name": "Sara",
    "last_name": "Ahmed",
    "email": "sara@example.com",
    "mobile_no": "+971500000000",
    "status": "New",
    "source": "Website"
  }
}
```

### Update existing lead and set property

```json
{
  "lead": {
    "name": "CRM-LEAD-2026-00012",
    "custom_property": "PROP-2026-00001",
    "status": "Follow Up"
  }
}
```

## Response

```json
{
  "message": {
    "name": "CRM-LEAD-2026-00015",
    "custom_property": "PROP-2026-00001"
  }
}
```

(`message` is the standard Frappe wrapper for whitelisted methods.)

## Legacy alias

`crm.fcrm.api.lead.create_lead_against_property` still exists and calls the same implementation.
