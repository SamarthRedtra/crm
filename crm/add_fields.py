import frappe

def run():
    # 1. Create Off Plan Payment Installment
    if not frappe.db.exists("DocType", "Off Plan Payment Installment"):
        frappe.get_doc({
            "doctype": "DocType",
            "name": "Off Plan Payment Installment",
            "module": "FCRM",
            "custom": 0,
            "istable": 1,
            "fields": [
                {
                    "fieldname": "milestone",
                    "label": "Milestone",
                    "fieldtype": "Data",
                    "reqd": 1,
                    "in_list_view": 1
                },
                {
                    "fieldname": "percentage",
                    "label": "Percentage (%)",
                    "fieldtype": "Percent",
                    "reqd": 1,
                    "in_list_view": 1
                }
            ]
        }).insert(ignore_permissions=True)
        print("Created Off Plan Payment Installment")
    
    # 2. Create Project Unit
    if not frappe.db.exists("DocType", "Project Unit"):
        frappe.get_doc({
            "doctype": "DocType",
            "name": "Project Unit",
            "module": "FCRM",
            "custom": 0,
            "istable": 1,
            "fields": [
                {
                    "fieldname": "layout_type",
                    "label": "Layout Type",
                    "fieldtype": "Data",
                    "reqd": 1,
                    "in_list_view": 1
                },
                {
                    "fieldname": "size",
                    "label": "Size (sqft)",
                    "fieldtype": "Float",
                    "in_list_view": 1
                },
                {
                    "fieldname": "bathrooms",
                    "label": "No. of Bathrooms",
                    "fieldtype": "Int",
                    "in_list_view": 1
                },
                {
                    "fieldname": "floor_plan",
                    "label": "Floor Plan",
                    "fieldtype": "Attach Image"
                }
            ]
        }).insert(ignore_permissions=True)
        print("Created Project Unit")

    # 3. Add fields to Property DocType
    property_doc = frappe.get_doc("DocType", "Property")
    existing_fieldnames = [f.fieldname for f in property_doc.fields]
    
    new_fields = [
        {
            "fieldname": "trakheesi_permit_number",
            "label": "Trakheesi Permit Number",
            "fieldtype": "Data",
            "depends_on": "eval:doc.completion_status == 'Off-Plan'",
            "mandatory_depends_on": "eval:doc.completion_status == 'Off-Plan'"
        },
        {
            "fieldname": "trakheesi_qr_code",
            "label": "Trakheesi QR Code",
            "fieldtype": "Attach Image",
            "depends_on": "eval:doc.completion_status == 'Off-Plan'",
            "mandatory_depends_on": "eval:doc.completion_status == 'Off-Plan'"
        },
        {
            "fieldname": "zone_name",
            "label": "Zone Name",
            "fieldtype": "Data",
            "depends_on": "eval:doc.completion_status == 'Off-Plan'",
            "mandatory_depends_on": "eval:doc.completion_status == 'Off-Plan'"
        },
        {
            "fieldname": "offplan_section",
            "label": "Off-Plan Details",
            "fieldtype": "Section Break",
            "depends_on": "eval:doc.completion_status == 'Off-Plan'"
        },
        {
            "fieldname": "payment_plan_table",
            "label": "Payment Plan",
            "fieldtype": "Table",
            "options": "Off Plan Payment Installment",
            "depends_on": "eval:doc.completion_status == 'Off-Plan'"
        },
        {
            "fieldname": "project_units_table",
            "label": "Project Units (Admin Only)",
            "fieldtype": "Table",
            "options": "Project Unit",
            "depends_on": "eval:doc.completion_status == 'Off-Plan'"
        }
    ]

    if "trakheesi_permit_number" not in existing_fieldnames:
        idx_to_insert = 0
        for i, f in enumerate(property_doc.fields):
            if f.fieldname == "off_plan_agencies":
                idx_to_insert = i + 1
                break
        
        if idx_to_insert == 0:
            idx_to_insert = len(property_doc.fields)
            
        # Rebuild the fields list preserving order
        fields_before = property_doc.fields[:idx_to_insert]
        fields_after = property_doc.fields[idx_to_insert:]
        
        # Clear existing fields
        property_doc.set("fields", [])
        
        # Add back before
        for f in fields_before:
            property_doc.append("fields", f)
            
        # Add new fields
        for f in new_fields:
            property_doc.append("fields", f)
            
        # Add back after
        for f in fields_after:
            property_doc.append("fields", f)

        property_doc.save(ignore_permissions=True)
        frappe.db.commit()
        print("Updated Property DocType")
    else:
        print("Fields already exist in Property DocType")

