import frappe
from crm.api.redtra.agents import get_agent, list_agents
from crm.api.redtra.agencies import get_agency, list_agencies

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
    verify_agent_api()
    verify_agency_api()
