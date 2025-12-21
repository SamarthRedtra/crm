# Redtra API - Sequence Diagrams

Visual representations of API workflows and doctype interactions. These diagrams help developers understand the flow of data and operations in the Redtra Property Booking System.

## Table of Contents

1. [Customer Browsing and Booking Appointment](#1-customer-browsing-and-booking-appointment-flow)
2. [Agent Setting Up Availability](#2-agent-setting-up-availability-flow)
3. [Agent Managing Appointments and Properties](#3-agent-managing-appointments-and-properties-flow)
4. [Notification System](#4-notification-system-flow)
5. [Property Creation with Child Tables](#5-property-creation-with-child-tables-flow)
6. [Agent Verification Check](#6-agent-verification-check-flow)
7. [Doctype Relationships](#7-doctype-relationships-overview)

---

## 1. Customer Browsing and Booking Appointment Flow

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

**Key Points:**
- Properties and agent availability can be viewed without authentication
- Appointment booking requires authentication
- Appointments validate against agent's availability schedule and existing bookings
- Notifications are automatically created for both customer and agent

---

## 2. Agent Setting Up Availability Flow

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

**Key Points:**
- Agents authenticate first
- Availability slots are stored in a child table (`Agent Availability Slot`)
- Existing slots are replaced (not merged) when updating
- Each slot defines: day of week, start time, end time
- `max_appointment_minutes` defines the duration for appointment slots

---

## 3. Agent Managing Appointments and Properties Flow

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

**Key Points:**
- Agent dashboard aggregates data from multiple doctypes
- Properties include child tables (Amenities, Images)
- Appointments can be rescheduled by the agent
- Calendar events are automatically maintained

---

## 4. Notification System Flow

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

**Key Points:**
- Notifications are created automatically when appointments are booked
- Two notifications are created: one for customer, one for agent
- Notifications reference the appointment document
- Users can mark notifications as read

---

## 5. Property Creation with Child Tables Flow

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

**Key Points:**
- Property is created first (parent document)
- Child tables (Amenities, Gallery) are created separately
- Each child table row references the parent property
- The complete property with child tables is returned

---

## 6. Agent Verification Check Flow

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

**Key Points:**
- Verification check is controlled by a system setting
- When enabled, only verified agents are accessible
- When disabled, all agents are accessible regardless of status
- Applies to: Get Agent, Get Available Slots, Create Appointment

---

## 7. Doctype Relationships Overview

This diagram shows the relationships between different doctypes in the system.

```mermaid
erDiagram
    User ||--o| Agent : "has"
    Agent ||--o{ Property : "owns"
    Agent ||--o{ "Agent Availability Slot" : "has"
    Property ||--o{ "Property Amenity" : "has"
    Property ||--o{ "Property Image" : "has"
    Property ||--o{ "Property Appointment" : "has"
    "Property Appointment" }o--|| Agent : "assigned to"
    "Property Appointment" }o--|| Customer : "booked by"
    "Property Appointment" ||--o| "Calendar Event" : "creates"
    "Property Appointment" ||--o{ "CRM Notification" : "generates"
    Agent }o--|| Area : "operates in"
    Property }o--|| Area : "located in"
    Property }o--|| Developer : "developed by"
    "Property Setting" ||--|| System : "configured by"

    User {
        string email PK
        string full_name
        string phone
    }
    
    Agent {
        string name PK
        string user FK
        string status
        int max_appointment_minutes
        int max_daily_appointments
    }
    
    "Agent Availability Slot" {
        string name PK
        string parent FK
        string day_of_week
        time start_time
        time end_time
    }
    
    Property {
        string name PK
        string agent FK
        string area_id FK
        string developer_id FK
        string title
        decimal price
        string listing_type
    }
    
    "Property Amenity" {
        string name PK
        string parent FK
        string amenity_name FK
    }
    
    "Property Image" {
        string name PK
        string parent FK
        string image
        string caption
        int sort_order
    }
    
    "Property Appointment" {
        string name PK
        string property FK
        string agent FK
        string customer FK
        datetime start_datetime
        datetime end_datetime
        string status
        string calendar_event FK
    }
    
    "CRM Notification" {
        string name PK
        string from_user FK
        string to_user FK
        string notification_type
        string notification_text
        string reference_doctype
        string reference_docname FK
        int read
    }
    
    Area {
        string name PK
        string area_name
        string city
    }
    
    Developer {
        string name PK
        string developer_name
        string status
    }
    
    "Property Setting" {
        string name PK
        int mandate_agent_verification
    }
```

**Legend:**
- `||--o|` : One-to-One relationship
- `||--o{` : One-to-Many relationship
- `PK` : Primary Key
- `FK` : Foreign Key

---

## Key Doctype Structures

### Property Appointment DocType

```
Property Appointment (Parent)
├── property (Link: Property) - Required
├── agent (Link: Agent) - Required
├── customer (Link: Customer) - Required
├── start_datetime (Datetime) - Required
├── end_datetime (Datetime) - Required
├── status (Select) - Default: "Scheduled"
├── notes (Text)
└── calendar_event (Link: Event) - Auto-created
```

### Agent DocType

```
Agent (Parent)
├── user (Link: User) - Required
├── status (Select) - "Pending", "Verified", "Rejected"
├── max_appointment_minutes (Int) - Default: 30
├── max_daily_appointments (Int) - Default: 10
└── availability_slots (Child Table)
    └── Agent Availability Slot
        ├── day_of_week (Select) - Required
        ├── start_time (Time) - Required
        └── end_time (Time) - Required
```

### Property DocType

```
Property (Parent)
├── title (Data) - Required
├── agent (Link: Agent) - Required
├── listing_type (Select) - Required
├── property_type (Select) - Required
├── price (Currency) - Required
├── amenities (Child Table)
│   └── Property Amenity
│       └── amenity_name (Link: Amenity)
└── gallery (Child Table)
    └── Property Image
        ├── image (Attach Image)
        ├── caption (Data)
        └── sort_order (Int)
```

---

## Workflow Summary

### Customer Journey
1. Browse properties (public) → View details → Check agent availability
2. Login/Register → Select time slot → Book appointment
3. Receive notification → View appointments → Manage favorites

### Agent Journey
1. Login → Set availability schedule → Create properties
2. View appointments → Receive notifications → Manage dashboard
3. Update property details → Reschedule appointments

---

## Diagram Tools

These diagrams are in Mermaid format and can be rendered in:
- GitHub (native support)
- GitLab (native support)
- Markdown viewers with Mermaid support
- VS Code with Mermaid extension
- Online: https://mermaid.live/

To convert to images or other formats, use:
- Mermaid CLI: `mmdc -i diagram.mmd -o diagram.png`
- Online converters available

---

**For detailed API documentation, refer to `DEVELOPER_GUIDE.md`**
