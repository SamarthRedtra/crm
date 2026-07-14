import frappe
from crm.api.redtra.agents import get_agent, list_agents
from crm.api.redtra.agencies import get_agency, list_agencies


def verify_agency_isolation_data():
	"""Report records still missing agency and agents missing User Permission."""
	print("Verifying agency isolation data...")
	doctypes = ("Property", "CRM Lead", "Contact", "FCRM Note", "CRM Call Log")
	for doctype in doctypes:
		if not frappe.db.has_column(doctype, "agency"):
			continue
		missing = frappe.db.count(doctype, filters={"agency": ["in", ["", None]]})
		print(f"  {doctype}: {missing} record(s) missing agency")

	from frappe.core.doctype.user_permission.user_permission import user_permission_exists

	missing_perms = 0
	for agent in frappe.get_all(
		"Agent",
		filters={"agency": ["is", "set"], "user": ["is", "set"]},
		fields=["user", "agency"],
	):
		if not user_permission_exists(agent.user, "Agency", agent.agency, None):
			missing_perms += 1
	print(f"  Agents missing Agency User Permission: {missing_perms}")


def verify_crm_lead_fields():
    print("Verifying CRM Lead fields...")
    meta = frappe.get_meta("CRM Lead")
    fields = [f.fieldname for f in meta.fields]
    if "agent_id" in fields and "agency" in fields:
        print("PASS: agent_id and agency fields found in CRM Lead")
    else:
        print(f"FAIL: fields missing. Found: {fields}")

def verify_agent_api():
    print("\nVerifying Agent API...")
    # Find an agent
    agents = frappe.get_all("Agent", limit=1)
    if not agents:
        print("No agents found to test")
        return
    
    agent_id = agents[0].name
    print(f"Testing with agent: {agent_id}")
    
    # Test get_agent
    try:
        data = get_agent(agent_id)
        if "properties" in data:
            print(f"PASS: properties found in get_agent response. Count: {len(data['properties'])}")
        else:
            print("FAIL: properties key missing in get_agent response")
            
        if "leads" in data:
             print(f"PASS: leads stats found: {data['leads']}")
        else:
             print("FAIL: leads stats missing")
             
    except Exception as e:
        print(f"FAIL: get_agent raised exception: {e}")

def verify_agency_api():
    print("\nVerifying Agency API...")
    # Find an agency
    agencies = frappe.get_all("Agency", limit=1)
    if not agencies:
        print("No agencies found to test")
        return
        
    agency_id = agencies[0].name
    print(f"Testing with agency: {agency_id}")
    
    try:
        data = get_agency(agency_id)
        if "properties" in data:
             print(f"PASS: properties found in get_agency response. Count: {len(data['properties'])}")
        else:
            print("FAIL: properties key missing in get_agency response")
            
    except Exception as e:
        print(f"FAIL: get_agency raised exception: {e}")

if __name__ == "__main__":
    verify_crm_lead_fields()
    verify_agency_isolation_data()
    verify_agent_api()
    verify_agency_api()
