
__version__ = "2.0.0-dev"
__title__ = "Frappe CRM"

# Ensure Redtra API routes are registered on startup.
from crm.api.redtra import register_routes
from crm.api.patches import patch_frappe_api_handler


register_routes()
patch_frappe_api_handler()