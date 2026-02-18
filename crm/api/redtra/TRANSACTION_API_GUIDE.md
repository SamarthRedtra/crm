# Transaction API Developer Reference (v2)

This document outlines the updates to the Redtra Transaction API to support the new list view and advanced filtering.

## Endpoint: List Transactions
`GET /api/transactions`

**Auth:** Optional (Bearer token for agent-scoped data; guest access allowed for public listings).

### Query Parameters (Filters)
Combine these parameters in the query string to refine results:

| Parameter | Type | Description |
| --- | --- | --- |
| `off_plan` | `boolean` | `1` or `true` for off-plan; `0` or `false` for secondary market (Buy). |
| `property_type` | `string` | Filter by `Apartment`, `Villa`, `Office`, etc. (comma-separated). |
| `min_price` | `number` | Minimum transaction amount. |
| `max_price` | `number` | Maximum transaction amount. |
| `min_area` | `number` | Minimum property area in sq.ft. |
| `max_area` | `number` | Maximum property area in sq.ft. |
| `location` | `string` | Search query for area name, city, or property title. |

#### Filtering Examples
- **Filter by Off-Plan Villas**:
  `GET /api/transactions?off_plan=1&property_type=Villa`
- **Search by Location & Price Range**:
  `GET /api/transactions?location=Mirdif&min_price=1000000&max_price=5000000`
- **Multiple Property Types**:
  `GET /api/transactions?property_types=Apartment,Unit`

---

### Response Structure
The `items` array contains enriched property metadata and calculated metrics.

#### Attributes per Transaction
| Attribute | Type | Example | Description |
| --- | --- | --- | --- |
| `id` | `string` | `"TXN-00001"` | Transaction ID. |
| `formatted_amount` | `string` | `"3.55M"` | Condensed amount for UI display (K/M suffixes). |
| `price_per_sqft` | `float` | `3820.0` | Raw calculated rate. |
| `formatted_price_per_sqft` | `string` | `"3.82K"` | Condensed rate for UI (e.g., "$3.82K/sqft"). |
| `property_title` | `string` | `"Luxury Villa"` | Linked property name. |
| `property_image` | `url` | `"/files/img.jpg"` | Primary thumbnail. |
| `area_sqft` | `number` | `929` | Total area from the property record. |
| `property_type` | `string` | `"Villa"` | Type of property. |
| `location_area` | `string` | `"Mirdif"` | Specific area name. |
| `location_city` | `string` | `"Dubai"` | City name. |

#### Sample JSON Response
```json
{
  "items": [
    {
      "id": "TXN-2025-00001",
      "transaction_date": "2025-02-11",
      "amount": 3550000,
      "formatted_amount": "3.55M",
      "price_per_sqft": 3821.31,
      "formatted_price_per_sqft": "3.82K",
      "property_title": "Modern Villa in Mirdif",
      "property_type": "Villa",
      "location_area": "Mirdif",
      "area_sqft": 929,
      "property_image": "/files/villa_01.jpg",
      "currency": "AED",
      "transaction_type": "Sale"
    }
  ],
  "page": 1,
  "total_pages": 5
}
```
