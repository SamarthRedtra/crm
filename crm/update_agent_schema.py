import frappe

def run():
    # 1. Update Property DocType
    property_doc = frappe.get_doc("DocType", "Property")
    for f in property_doc.fields:
        if f.fieldname == "zone_name":
            f.mandatory_depends_on = ""
            break
    property_doc.save(ignore_permissions=True)
    frappe.db.commit()
    print("Updated Property DocType")

    # 2. Update Agent DocType
    agent_doc = frappe.get_doc("DocType", "Agent")
    existing_fieldnames = [f.fieldname for f in agent_doc.fields]
    
    new_fields = [
        {
            "fieldname": "trakheesi_permit_number",
            "label": "Trakheesi Permit Number",
            "fieldtype": "Data",
            "reqd": 1,
            "in_list_view": 1
        },
        {
            "fieldname": "trakheesi_qr_code",
            "label": "Trakheesi QR Code",
            "fieldtype": "Attach Image",
            "reqd": 1
        },
        {
            "fieldname": "zone_name",
            "label": "Zone Name",
            "fieldtype": "Data",
            "reqd": 0,
            "in_list_view": 1
        }
    ]

    if "trakheesi_permit_number" not in existing_fieldnames:
        # Insert them after 'dfd_registration_id'
        idx_to_insert = 0
        for i, f in enumerate(agent_doc.fields):
            if f.fieldname == "dfd_registration_id":
                idx_to_insert = i + 1
                break
        
        if idx_to_insert == 0:
            idx_to_insert = len(agent_doc.fields)
            
        fields_before = agent_doc.fields[:idx_to_insert]
        fields_after = agent_doc.fields[idx_to_insert:]
        
        agent_doc.set("fields", [])
        
        for f in fields_before:
            agent_doc.append("fields", f)
            
        for f in new_fields:
            agent_doc.append("fields", f)
            
        for f in fields_after:
            agent_doc.append("fields", f)

        agent_doc.save(ignore_permissions=True)
        frappe.db.commit()
        print("Updated Agent DocType")
    else:
        print("Fields already exist in Agent DocType")

