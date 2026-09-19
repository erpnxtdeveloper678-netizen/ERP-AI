import frappe
from erp_ai.ai.decorators import ai_tool


@ai_tool(name="ping", description="Check ERP connectivity.")
def ping():
    return {"success": True, "message": "ERP is online."}


@ai_tool(name="current_user", description="Return the current logged-in user and their roles.")
def current_user():
    return {
        "user": frappe.session.user,
        "roles": frappe.get_roles(frappe.session.user),
    }
