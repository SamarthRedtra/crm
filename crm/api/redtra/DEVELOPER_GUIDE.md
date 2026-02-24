# Redtra Property API - Developer Guide

A comprehensive guide for developers to integrate with the Redtra Property Booking API.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication](#authentication)
3. [API Endpoints Overview](#api-endpoints-overview)
4. [Sequence Diagrams](#sequence-diagrams)
5. [Common Workflows](#common-workflows)
6. [Error Handling](#error-handling)
7. [Best Practices](#best-practices)

---

## Getting Started

### Base URL

All API requests should be made to:
```
https://your-domain.com/api
```

Replace `your-domain.com` with your actual domain name.

### Content Type

All requests should include:
```
Content-Type: application/json
```

### Response Format

All responses are in JSON format.

---

## Authentication

The API uses JWT (JSON Web Token) for authentication. Most endpoints require a valid token.

### Step 1: Register or Login

**Register a New User**
```http
POST /api/auth/register
Content-Type: application/json

{
  "full_name": "John Doe",
  "email": "john@example.com",
  "password": "SecurePassword123!",
  "phone": "+971501234567"
}
```

**Register as Agent**
```http
POST /api/auth/register
Content-Type: application/json

{
  "full_name": "Jane Agent",
  "email": "jane@example.com",
  "password": "SecurePassword123!",
  "phone": "+971501234567",
  "is_agent": true,
  "whatsapp_number": "+971501234568",
  "bio": "10 years of experience in Dubai real estate"
}
```

**Login**
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "SecurePassword123!"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user_id": "john@example.com",
  "full_name": "John Doe"
}
```

### Step 2: Use the Token

Include the token in all subsequent requests:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Public Endpoints (No Authentication Required)

These endpoints work without a token:
- `GET /api/properties` - List properties
- `GET /api/properties/{property_id}` - Get property details
- `GET /api/agents` - List agents
- `GET /api/agents/{agent_id}` - Get agent details
- `GET /api/agents/{agent_id}/available-slots` - Get agent availability
- `GET /api/areas` - List areas
- `GET /api/areas/{area_id}` - Get area details
- `GET /api/developers` - List developers
- `GET /api/developers/{developer_id}` - Get developer details
- `GET /api/home` - Get home page data

---

## API Endpoints Overview

### 1. Properties

#### List Properties (Public)
```http
GET /api/properties?page=1&page_size=20&listing_type=Sale&city=Dubai
```

**Query Parameters:**
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20, max: 100)
- `listing_type` - Filter: "Buy" or "Rent"
- `completion_status` - Filter: "All", "Ready", or "Off-plan"
- `property_type` - Filter: "Apartment", "Villa", "Office", "Shop", "Plot", "Other"
- `property_category` - Filter: "Residential", "Commercial", "Mixed Use"
- `min_price`, `max_price` - Price range
- `bedrooms`, `bathrooms` - Number of bedrooms/bathrooms
- `min_area`, `max_area` - Area range (sq.ft)
- `amenities` - Filter by amenities (e.g., "Pool", "Gym")
- `city`, `state`, `location` - Location filters
- `agent` - Filter by agent ID
- `is_featured` - Show only featured properties

**Example Response:**
```json
{
  "items": [
    {
      "id": "PROP-2025-00001",
      "title": "2 BHK Apartment in Downtown",
      "listing_type": "Sale",
      "property_type": "Apartment",
      "price": 3500000,
      "currency": "AED",
      "bedrooms": 2,
      "bathrooms": 2,
      "area_sqft": 1200,
      "city": "Dubai",
      "primary_image_url": "https://example.com/image.jpg",
      "amenities": ["Pool", "Gym", "Parking"],
      "gallery": [
        {
          "image": "https://example.com/gallery1.jpg",
          "caption": "Living Room",
          "sort_order": 1
        }
      ]
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_items": 150,
  "total_pages": 8
}
```

#### Get Property Details (Public)
```http
GET /api/properties/PROP-2025-00001
```

**Response includes:**
- Full property details
- Amenities list
- Gallery images
- Agent information
- Developer information
- WhatsApp chat link

#### Create Property (Agent Only)
```http
POST /api/properties
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Luxury 3 BHK Villa in Palm Jumeirah",
  "listing_type": "Sale",
  "property_type": "Villa",
  "property_category": "Residential",
  "price": 8500000,
  "currency": "AED",
  "bedrooms": 3,
  "bathrooms": 3,
  "furnishing_status": "Furnished",
  "area_sqft": 2500,
  "area_id": "AREA-0001",
  "developer_id": "DEV-00001",
  "address_line1": "Palm Jumeirah, Frond A",
  "city": "Dubai",
  "state": "Dubai",
  "country": "United Arab Emirates",
  "pincode": "12345",
  "latitude": 25.1125,
  "longitude": 55.1392,
  "description": "Stunning waterfront villa with private beach access",
  "primary_image": "https://example.com/villa-main.jpg",
  "is_featured": true,
  "amenities": [
    "Pool",
    "Gym",
    "Beach Access",
    "Parking",
    "Security"
  ],
  "gallery": [
    {
      "image": "https://example.com/villa-1.jpg",
      "caption": "Living Room",
      "sort_order": 1
    },
    {
      "image": "https://example.com/villa-2.jpg",
      "caption": "Master Bedroom",
      "sort_order": 2
    }
  ]
}
```

**Required Fields:**
- `title` - Property title
- `listing_type` - "Buy" or "Rent"
- `completion_status` - "All", "Ready", or "Off-plan"
- `property_type` - "Apartment", "Villa", etc.
- `price` - Numeric value
- `currency` - Currency code (e.g., "AED", "USD")

#### Update Property (Agent Owner Only)
```http
PUT /api/properties/PROP-2025-00001
Authorization: Bearer <token>
Content-Type: application/json

{
  "price": 8200000,
  "description": "Updated description with new features"
}
```

#### Delete Property (Agent Owner Only)
```http
DELETE /api/properties/PROP-2025-00001
Authorization: Bearer <token>
```

---

### 2. Agents

#### List Agents (Public)
```http
GET /api/agents?page=1&page_size=20&status=Verified
```

**Query Parameters:**
- `page` - Page number
- `page_size` - Items per page
- `status` - Filter by status (default: "Verified")
- `search` - Search by agent name

**Response:**
```json
{
  "items": [
    {
      "id": "AGENT-0005",
      "name": "Jane Agent",
      "status": "Verified",
      "bio": "10 years experience",
      "phone": "+971501234567",
      "profile_image": "https://example.com/profile.jpg",
      "property_count": 25
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_items": 50,
  "total_pages": 3
}
```

#### Get Agent Details (Public)
```http
GET /api/agents/AGENT-0005
```

**Response includes:**
- Agent profile information
- Availability slots configuration
- Max appointment minutes
- List of properties
- Property count

#### Get Agent Available Slots (Public)
```http
GET /api/agents/AGENT-0005/available-slots?start_date=2025-12-15&end_date=2025-12-22
```

**Query Parameters:**
- `start_date` - Start date (YYYY-MM-DD), optional (defaults to today)
- `end_date` - End date (YYYY-MM-DD), optional (defaults to 7 days from start)

**Response:**
```json
{
  "agent_id": "AGENT-0005",
  "max_appointment_minutes": 30,
  "start_date": "2025-12-15",
  "end_date": "2025-12-22",
  "available_slots": [
    {
      "start_datetime": "2025-12-15 09:00:00",
      "end_datetime": "2025-12-15 09:30:00",
      "date": "2025-12-15",
      "time": "09:00"
    },
    {
      "start_datetime": "2025-12-15 09:30:00",
      "end_datetime": "2025-12-15 10:00:00",
      "date": "2025-12-15",
      "time": "09:30"
    }
  ]
}
```

#### Update Agent Availability (Agent Only)
```http
POST /api/agents/availability
Authorization: Bearer <token>
Content-Type: application/json

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
    },
    {
      "day_of_week": "Wednesday",
      "start_time": "09:00:00",
      "end_time": "17:00:00"
    },
    {
      "day_of_week": "Thursday",
      "start_time": "09:00:00",
      "end_time": "17:00:00"
    },
    {
      "day_of_week": "Friday",
      "start_time": "09:00:00",
      "end_time": "13:00:00"
    }
  ]
}
```

**Important Notes:**
- This endpoint updates the logged-in agent's availability
- `day_of_week` must be: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, or Sunday
- `start_time` and `end_time` format: "HH:MM:SS" or "HH:MM"
- `end_time` must be after `start_time`
- All existing slots are replaced with the new ones provided

---

### 3. Appointments

#### List Appointments (Authenticated)
```http
GET /api/appointments
Authorization: Bearer <token>
```

**Response:** List of appointments for the current user (customer sees their appointments, agent sees their appointments)

#### Create Appointment (Customer Only)
```http
POST /api/appointments
Authorization: Bearer <token>
Content-Type: application/json

{
  "property_id": "PROP-2025-00001",
  "start_datetime": "2025-12-15 10:00:00",
  "end_datetime": "2025-12-15 10:30:00",
  "notes": "Interested in viewing the property"
}
```

**Important Notes:**
- The appointment duration must match the agent's `max_appointment_minutes`
- The slot must be within the agent's availability hours
- The slot must align with the appointment duration boundaries
- Automatically creates notifications for both customer and agent

**Response:**
```json
{
  "id": "APPT-2025-00001",
  "status": "Scheduled",
  "start_datetime": "2025-12-15 10:00:00",
  "end_datetime": "2025-12-15 10:30:00",
  "property": {
    "id": "PROP-2025-00001",
    "title": "2 BHK Apartment"
  },
  "agent": {
    "id": "AGENT-0005",
    "name": "Jane Agent"
  },
  "customer": {
    "id": "CUST-0001",
    "name": "John Doe"
  }
}
```

#### Get Appointment Details
```http
GET /api/appointments/APPT-2025-00001
Authorization: Bearer <token>
```

#### Update Appointment
```http
PUT /api/appointments/APPT-2025-00001
Authorization: Bearer <token>
Content-Type: application/json

{
  "start_datetime": "2025-12-15 11:00:00",
  "end_datetime": "2025-12-15 11:30:00",
  "notes": "Rescheduled to later time"
}
```

#### Cancel Appointment
```http
DELETE /api/appointments/APPT-2025-00001
Authorization: Bearer <token>
```

---

### 4. User Profile

#### Get Profile
```http
GET /api/user/profile
Authorization: Bearer <token>
```

**For Customers:**
```json
{
  "user_id": "john@example.com",
  "full_name": "John Doe",
  "email": "john@example.com",
  "phone": "+971501234567",
  "whatsapp_number": "+971501234567",
  "preferred_city": "Dubai"
}
```

**For Agents:**
```json
{
  "user_id": "jane@example.com",
  "full_name": "Jane Agent",
  "email": "jane@example.com",
  "phone": "+971501234567",
  "agent_profile": {
    "id": "AGENT-0005",
    "status": "Verified",
    "about_me": "10 years experience",
    "max_daily_appointments": 10
  },
  "appointments_today": [...],
  "properties": [...],
  "lead_stats": {
    "total": 150,
    "today": 5,
    "trend_ratio": 0.25
  }
}
```

#### Update Profile
```http
PUT /api/user/profile
Authorization: Bearer <token>
Content-Type: application/json

{
  "full_name": "John Doe Updated",
  "phone": "+971509876543",
  "whatsapp_number": "+971509876543",
  "preferred_city": "Abu Dhabi"
}
```

**For Agents, you can also update:**
```json
{
  "about_me": "Updated bio",
  "profile_image": "https://example.com/new-profile.jpg",
  "max_daily_appointments": 15
}
```

---

### 5. Notifications

#### List Notifications
```http
GET /api/notifications?page=1&page_size=20&unread_only=true
Authorization: Bearer <token>
```

**Query Parameters:**
- `page` - Page number
- `page_size` - Items per page
- `unread_only` - If true, returns only unread notifications

**Response:**
```json
{
  "items": [
    {
      "id": "NOTIF-0001",
      "created_at": "2025-12-15 10:00:00",
      "type": "Assignment",
      "title": "New appointment booked: 2 BHK Apartment",
      "message": "New appointment booked for <b>2 BHK Apartment</b> on <b>15 Dec 2025, 10:00 AM</b>. Customer: John Doe",
      "read": false,
      "from_user": {
        "id": "customer@example.com",
        "full_name": "John Doe"
      },
      "reference": {
        "doctype": "Property Appointment",
        "name": "APPT-2025-00001"
      }
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_items": 10,
  "total_pages": 1
}
```

#### Mark Notifications as Read
```http
POST /api/notifications/mark-read
Authorization: Bearer <token>
Content-Type: application/json

{
  "notification_ids": ["NOTIF-0001", "NOTIF-0002"]
}
```

**To mark all as read, send empty array:**
```json
{
  "notification_ids": []
}
```

---

### 6. Favorites

#### List Favorites
```http
GET /api/favorites
Authorization: Bearer <token>
```

#### Add to Favorites
```http
POST /api/favorites
Authorization: Bearer <token>
Content-Type: application/json

{
  "property_id": "PROP-2025-00001"
}
```

#### Remove from Favorites
```http
DELETE /api/favorites/PROP-2025-00001
Authorization: Bearer <token>
```

---

### 7. Areas

#### List Areas
```http
GET /api/areas?page=1&page_size=20&city=Dubai
```

#### Get Area Details
```http
GET /api/areas/AREA-0001
```

#### List Properties in Area
```http
GET /api/areas/AREA-0001/properties?page=1&page_size=20
Authorization: Bearer <token>
```

---

### 8. Developers

#### List Developers
```http
GET /api/developers?page=1&page_size=20&status=Active
```

#### Get Developer Details
```http
GET /api/developers/DEV-00001
```

#### List Developer Properties
```http
GET /api/developers/DEV-00001/properties?page=1&page_size=20
```

---

## Sequence Diagrams

Visual representations of how the API endpoints interact with each other and the underlying Frappe doctypes.

> **📋 Full Diagram Documentation:** For detailed sequence diagrams with additional workflows and doctype relationship diagrams, see [`SEQUENCE_DIAGRAMS.md`](./SEQUENCE_DIAGRAMS.md)

### 1. Customer Browsing and Booking Appointment Flow

This diagram shows the complete flow when a customer browses properties and books an appointment.

```mermaid
sequenceDiagram
    participant C as Customer (Mobile App/Web)
    participant API as Redtra API
    participant DB as Frappe Database
    participant Agent as Agent
    participant Notif as Notification System

    Note over C,Notif: Public Browsing (No Auth Required)
    C->>API: GET /api/properties?city=Dubai
    API->>DB: Query Property DocType
    DB-->>API: List of Properties
    API-->>C: Properties List (with amenities & gallery)

    C->>API: GET /api/properties/PROP-001
    API->>DB: Fetch Property + Agent + Developer
    DB-->>API: Property Details
    API-->>C: Full Property Details

    C->>API: GET /api/agents/AGENT-005/available-slots?start_date=2025-12-15
    API->>DB: Fetch Agent DocType + Availability Slots (Child Table)
    API->>DB: Query Property Appointment DocType (existing bookings)
    DB-->>API: Agent Schedule + Booked Slots
    API->>API: Calculate Available Slots
    API-->>C: Available Time Slots

    Note over C,Notif: Authentication Required
    C->>API: POST /api/auth/login {email, password}
    API->>DB: Validate User Credentials
    DB-->>API: User Valid
    API-->>C: JWT Token

    Note over C,Notif: Booking Appointment
    C->>API: POST /api/appointments {property_id, start_datetime, end_datetime}
    API->>DB: Fetch Agent from Property
    API->>DB: Fetch Agent DocType + Availability Slots
    API->>API: Validate Slot Availability
    API->>API: Validate Appointment Duration (max_appointment_minutes)
    API->>DB: Check Existing Appointments (no conflicts)
    
    alt Slot Available & Valid
        API->>DB: Create Property Appointment DocType
        DB-->>API: Appointment Created
        API->>DB: Create Calendar Event (linked)
        API->>Notif: Create Notification (Customer)
        API->>Notif: Create Notification (Agent)
        API->>DB: Save CRM Notification DocType (2 records)
        API-->>C: 201 Created - Appointment Details
        Notif->>Agent: Push Notification (optional)
        Notif->>C: Push Notification (optional)
    else Slot Not Available
        API-->>C: 422 Validation Error
    end
```

### 2. Agent Setting Up Availability Flow

This diagram shows how an agent configures their weekly availability schedule.

```mermaid
sequenceDiagram
    participant A as Agent (Mobile App/Web)
    participant API as Redtra API
    participant DB as Frappe Database
    participant Auth as Auth System

    A->>API: POST /api/auth/login {email, password}
    API->>Auth: Validate Credentials
    Auth-->>API: User + Roles (Agent)
    API-->>A: JWT Token

    Note over A,DB: Setting Availability Schedule
    A->>API: POST /api/agents/availability<br/>{max_appointment_minutes, availability_slots}
    API->>Auth: Verify Token & Agent Role
    Auth-->>API: Authenticated Agent
    
    API->>DB: Fetch Agent DocType (by user)
    DB-->>API: Agent Record
    
    API->>API: Validate availability_slots data<br/>(day_of_week, start_time, end_time)
    
    alt Valid Data
        API->>DB: Clear existing Agent Availability Slot<br/>(Child Table rows)
        API->>DB: Insert new Agent Availability Slot rows<br/>(Child Table)
        API->>DB: Update max_appointment_minutes field
        DB-->>API: Success
        API->>DB: Fetch updated Agent DocType
        DB-->>API: Agent with Availability Slots
        API-->>A: 200 OK - Updated Agent Details
    else Invalid Data
        API-->>A: 422 Validation Error
    end
```

### 3. Agent Viewing Appointments and Managing Properties Flow

This diagram shows how an agent manages their appointments and properties.

```mermaid
sequenceDiagram
    participant A as Agent
    participant API as Redtra API
    participant DB as Frappe Database
    participant Prop as Property DocType
    participant Appt as Property Appointment DocType
    participant Notif as Notification System

    A->>API: GET /api/user/profile (with Bearer Token)
    API->>DB: Fetch User + Agent DocType
    DB-->>API: Agent Profile
    API->>DB: Query Property DocType (agent filter)
    DB-->>API: Agent's Properties
    API->>DB: Query Property Appointment DocType (today)
    DB-->>API: Today's Appointments
    API->>DB: Query Lead Stats
    DB-->>API: Statistics
    API-->>A: Agent Dashboard Data

    A->>API: GET /api/appointments (with Bearer Token)
    API->>DB: Query Property Appointment DocType<br/>(filtered by agent)
    DB-->>API: Agent's Appointments
    API-->>A: Appointments List

    A->>API: GET /api/notifications?unread_only=true
    API->>DB: Query CRM Notification DocType<br/>(to_user = agent)
    DB-->>API: Unread Notifications
    API-->>A: Notifications List

    Note over A,Prop: Creating a Property
    A->>API: POST /api/properties {title, listing_type, ...}
    API->>DB: Validate Agent Permissions
    API->>DB: Create Property DocType
    API->>DB: Create Property Amenity (Child Table rows)
    API->>DB: Create Property Image (Child Table rows)
    DB-->>API: Property Created
    API-->>A: 201 Created - Property Details

    Note over A,Appt: Rescheduling Appointment
    A->>API: PUT /api/appointments/APPT-001<br/>{start_datetime, end_datetime}
    API->>DB: Fetch Property Appointment DocType
    API->>DB: Validate Agent Ownership
    API->>DB: Update Appointment
    API->>DB: Update Calendar Event (linked)
    DB-->>API: Updated
    API-->>A: 200 OK - Updated Appointment
```

### 4. Notification System Flow

This diagram details how notifications are created and retrieved.

```mermaid
sequenceDiagram
    participant Appt as Appointment API
    participant Notif as Notification System
    participant DB as Frappe Database
    participant C as Customer
    participant A as Agent

    Note over Appt,A: When Appointment is Created
    Appt->>Notif: _create_appointment_notifications()
    Notif->>DB: Fetch Property, Customer, Agent
    DB-->>Notif: Document Details
    
    Note over Notif,DB: Create Customer Notification
    Notif->>DB: Create CRM Notification DocType<br/>(from_user: agent, to_user: customer)
    DB-->>Notif: Notification 1 Created
    
    Note over Notif,DB: Create Agent Notification
    Notif->>DB: Create CRM Notification DocType<br/>(from_user: customer, to_user: agent)
    DB-->>Notif: Notification 2 Created
    
    Notif-->>Appt: Notifications Created

    Note over C,A: Retrieving Notifications
    C->>DB: GET /api/notifications<br/>(via API with JWT)
    DB->>DB: Query CRM Notification<br/>(to_user = customer)
    DB-->>C: Customer Notifications
    
    A->>DB: GET /api/notifications<br/>(via API with JWT)
    DB->>DB: Query CRM Notification<br/>(to_user = agent)
    DB-->>A: Agent Notifications
    
    C->>DB: POST /api/notifications/mark-read<br/>{notification_ids: [...]}
    DB->>DB: Update CRM Notification<br/>(read = 1)
    DB-->>C: Marked as Read
```

### 5. Property Creation with Child Tables Flow

This diagram shows how property creation works with child tables (Amenities, Gallery).

```mermaid
sequenceDiagram
    participant Agent as Agent
    participant API as Property API
    participant DB as Frappe Database
    participant Prop as Property DocType
    participant Amenity as Property Amenity<br/>(Child Table)
    participant Gallery as Property Image<br/>(Child Table)
    participant Area as Area DocType
    participant Dev as Developer DocType

    Agent->>API: POST /api/properties<br/>{title, price, amenities[], gallery[]}
    
    API->>API: Validate Required Fields
    API->>DB: Validate Area (if area_id provided)
    Area-->>API: Area Valid
    
    API->>DB: Validate Developer (if developer_id provided)
    Dev-->>API: Developer Valid & Active
    
    API->>DB: Create Property DocType (Parent)
    Prop-->>API: Property Created (PROP-001)
    
    loop For Each Amenity
        API->>DB: Validate Amenity DocType exists
        API->>DB: Create Property Amenity<br/>(Child Table row)<br/>parent: PROP-001
        Amenity-->>API: Amenity Linked
    end
    
    loop For Each Gallery Image
        API->>DB: Create Property Image<br/>(Child Table row)<br/>parent: PROP-001
        Gallery-->>API: Image Linked
    end
    
    API->>DB: Fetch Complete Property<br/>(with child tables)
    DB-->>API: Property + Amenities + Gallery
    API-->>Agent: 201 Created - Complete Property Details
```

### 6. Agent Verification Check Flow

This diagram shows how the conditional agent verification works.

```mermaid
sequenceDiagram
    participant User as User/Customer
    participant API as API Endpoints
    participant Setting as Property Setting<br/>(Single DocType)
    participant Agent as Agent DocType
    participant DB as Database

    User->>API: GET /api/agents/AGENT-005
    API->>Setting: get_mandate_agent_verification()
    Setting->>DB: Fetch Property Setting DocType
    DB-->>Setting: mandate_agent_verification = true/false
    Setting-->>API: Verification Required: true/false
    
    alt Verification Required (true)
        API->>DB: Fetch Agent DocType
        DB-->>API: Agent Status = "Verified"/"Pending"/etc.
        
        alt Agent is Verified
            API->>DB: Fetch Agent Details + Properties
            DB-->>API: Complete Agent Data
            API-->>User: 200 OK - Agent Details
        else Agent Not Verified
            API-->>User: 403 Permission Error<br/>"Agent is not verified"
        end
    else Verification Not Required (false)
        API->>DB: Fetch Agent DocType (any status)
        DB-->>API: Agent Data
        API-->>User: 200 OK - Agent Details<br/>(verification check skipped)
    end
```

---

## Common Workflows

### Workflow 1: Customer Browsing and Booking Property

1. **Browse Properties (Public)**
   ```http
   GET /api/properties?listing_type=Sale&city=Dubai&bedrooms=2
   ```

2. **View Property Details (Public)**
   ```http
   GET /api/properties/PROP-2025-00001
   ```

3. **Check Agent Availability (Public)**
   ```http
   GET /api/agents/AGENT-0005/available-slots?start_date=2025-12-15&end_date=2025-12-22
   ```

4. **Login or Register**
   ```http
   POST /api/auth/login
   {
     "email": "customer@example.com",
     "password": "password"
   }
   ```

5. **Book Appointment**
   ```http
   POST /api/appointments
   Authorization: Bearer <token>
   {
     "property_id": "PROP-2025-00001",
     "start_datetime": "2025-12-15 10:00:00",
     "end_datetime": "2025-12-15 10:30:00"
   }
   ```

6. **Check Notifications**
   ```http
   GET /api/notifications?unread_only=true
   Authorization: Bearer <token>
   ```

---

### Workflow 2: Agent Managing Properties and Availability

1. **Login**
   ```http
   POST /api/auth/login
   {
     "email": "agent@example.com",
     "password": "password"
   }
   ```

2. **Set Availability Schedule**
   ```http
   POST /api/agents/availability
   Authorization: Bearer <token>
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

3. **Create Property**
   ```http
   POST /api/properties
   Authorization: Bearer <token>
   {
     "title": "New Property",
     "listing_type": "Sale",
     "property_type": "Apartment",
     "price": 500000,
     "currency": "AED"
   }
   ```

4. **View Appointments**
   ```http
   GET /api/appointments
   Authorization: Bearer <token>
   ```

5. **Check Notifications**
   ```http
   GET /api/notifications
   Authorization: Bearer <token>
   ```

---

## Error Handling

### Common HTTP Status Codes

- **200 OK** - Request successful
- **201 Created** - Resource created successfully
- **204 No Content** - Operation successful, no content to return
- **400 Bad Request** - Invalid request data
- **401 Unauthorized** - Missing or invalid authentication token
- **403 Forbidden** - Authenticated but lacks required permissions
- **404 Not Found** - Resource not found
- **422 Validation Error** - Validation failed (missing fields, invalid data)

### Error Response Format

```json
{
  "exception": "ValidationError",
  "exc_type": "ValidationError",
  "_error_message": "Missing required fields: title, price"
}
```

### Common Errors

**1. Invalid Token**
```json
{
  "_error_message": "Missing bearer token."
}
```
**Solution:** Re-login to get a fresh token

**2. Validation Error**
```json
{
  "_error_message": "Appointment duration must be exactly 30 minutes."
}
```
**Solution:** Check the agent's `max_appointment_minutes` and match the duration

**3. Permission Error**
```json
{
  "_error_message": "You can only update your own availability."
}
```
**Solution:** Ensure you're using your own agent account

**4. Slot Not Available**
```json
{
  "_error_message": "The requested time slot conflicts with an existing appointment."
}
```
**Solution:** Choose a different time slot from the available slots

---

## Best Practices

### 1. Token Management
- Store tokens securely (use secure storage in mobile apps)
- Tokens expire after 24 hours - implement refresh logic
- Handle token expiration gracefully - redirect to login

### 2. Error Handling
- Always check HTTP status codes
- Display user-friendly error messages
- Log errors for debugging

### 3. Caching
- Cache static data (areas, developers) - refresh periodically
- Cache property lists with appropriate cache invalidation
- Don't cache user-specific data (appointments, notifications)

### 4. Performance
- Use pagination for large lists (default page_size: 20)
- Implement infinite scroll or "Load More" buttons
- Avoid unnecessary API calls - batch operations when possible

### 5. User Experience
- Show loading states during API calls
- Implement optimistic updates where appropriate
- Provide clear feedback on success/failure

### 6. Appointment Booking
- Always fetch available slots before showing booking options
- Validate slot availability on the client side before submitting
- Handle conflicts gracefully - suggest alternative slots

### 7. Image Handling
- Use CDN URLs for images
- Implement image caching and lazy loading
- Handle image load failures gracefully

---

## Code Examples

### JavaScript/TypeScript (Fetch API)

```javascript
// Login
async function login(email, password) {
  const response = await fetch('https://your-domain.com/api/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password })
  });
  
  if (!response.ok) {
    throw new Error('Login failed');
  }
  
  const data = await response.json();
  // Store token securely
  localStorage.setItem('token', data.token);
  return data;
}

// Get Properties with Authentication
async function getProperties(filters = {}) {
  const token = localStorage.getItem('token');
  const queryParams = new URLSearchParams(filters).toString();
  
  const response = await fetch(
    `https://your-domain.com/api/properties?${queryParams}`,
    {
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
      }
    }
  );
  
  return response.json();
}

// Create Appointment
async function createAppointment(propertyId, startDatetime, endDatetime) {
  const token = localStorage.getItem('token');
  
  const response = await fetch('https://your-domain.com/api/appointments', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      property_id: propertyId,
      start_datetime: startDatetime,
      end_datetime: endDatetime
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error._error_message || 'Failed to create appointment');
  }
  
  return response.json();
}
```

### Python (Requests)

```python
import requests

BASE_URL = "https://your-domain.com/api"
token = None

def login(email, password):
    global token
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password}
    )
    response.raise_for_status()
    data = response.json()
    token = data["token"]
    return data

def get_properties(filters=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    response = requests.get(
        f"{BASE_URL}/properties",
        params=filters or {},
        headers=headers
    )
    response.raise_for_status()
    return response.json()

def create_appointment(property_id, start_datetime, end_datetime):
    response = requests.post(
        f"{BASE_URL}/appointments",
        json={
            "property_id": property_id,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    response.raise_for_status()
    return response.json()
```

### cURL Examples

```bash
# Login
curl -X POST https://your-domain.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'

# Get Properties (Public)
curl https://your-domain.com/api/properties?city=Dubai&listing_type=Sale

# Get Properties (Authenticated)
curl https://your-domain.com/api/properties \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Create Appointment
curl -X POST https://your-domain.com/api/appointments \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "PROP-2025-00001",
    "start_datetime": "2025-12-15 10:00:00",
    "end_datetime": "2025-12-15 10:30:00"
  }'
```

---

## Testing with Postman

1. **Import Collection**
   - Import `postman_collection.json` into Postman
   - Set the `base_url` variable to your domain

2. **Set Authentication**
   - Create a login request
   - Copy the token from response
   - Set as collection variable `token`
   - Collection is configured to use `{{token}}` automatically

3. **Test Workflows**
   - Use the pre-configured requests in the collection
   - Modify variables (`property_id`, `agent_id`, etc.) as needed

---

## Quick Reference

### Public Endpoints (No Auth)
- `GET /api/properties`
- `GET /api/properties/{id}`
- `GET /api/agents`
- `GET /api/agents/{id}`
- `GET /api/agents/{id}/available-slots`
- `GET /api/areas`
- `GET /api/areas/{id}`
- `GET /api/developers`
- `GET /api/developers/{id}`
- `GET /api/home`

### Protected Endpoints (Require Auth)
- `POST /api/auth/logout`
- `GET /api/user/profile`
- `PUT /api/user/profile`
- `POST /api/properties` (Agent only)
- `PUT /api/properties/{id}` (Agent owner only)
- `DELETE /api/properties/{id}` (Agent owner only)
- `POST /api/agents/availability` (Agent only)
- `POST /api/appointments` (Customer/Agent)
- `GET /api/appointments` (Authenticated)
- `GET /api/notifications` (Authenticated)
- `GET /api/favorites` (Authenticated)

---

## Support & Resources

- **Postman Collection:** `apps/crm/crm/api/redtra/postman_collection.json`
- **OpenAPI Spec:** `apps/crm/crm/api/redtra/openapi.yaml` or `openapi.json`
- **API Usage Guide:** `apps/crm/crm/api/redtra/API_USAGE.md`

For detailed endpoint documentation, refer to the OpenAPI specification file.

---

## Important Notes

1. **Agent Verification:** Agent verification checks are controlled by the `mandate_agent_verification` setting in Property Settings. When enabled, only verified agents can be accessed/booked.

2. **Availability Slots:** Agents must set up their availability schedule before appointments can be booked. Use `POST /api/agents/availability` to configure.

3. **Appointment Duration:** Appointments must match the agent's `max_appointment_minutes` setting exactly.

4. **Notifications:** Notifications are automatically created when appointments are booked - both customer and agent receive notifications.

5. **Image URLs:** Property images should be hosted on a CDN or file server. Provide full URLs in the API requests.

---

**Happy Coding! 🚀**


