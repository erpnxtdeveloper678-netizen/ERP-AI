import json
import frappe
from erp_ai.ai.registry import get_tool

def execute_tool(name: str, args: dict = None):
    """
    Dynamically executes a tool registered in the AI Registry with User Permissions Check.
    """
    if args is None:
        args = {}
        
    tool = get_tool(name)
    if not tool:
        raise ValueError(f"Tool '{name}' is not registered in the AI Registry.")
        
    func = tool.get("function")
    if not func:
        raise ValueError(f"No executable function found for tool '{name}'.")
        

    if any(action in name.lower() for action in ["cancel", "submit", "update", "delete", "create"]):
        docname = args.get("name") or args.get("docname")
        doctype = args.get("doctype")
        
        if doctype and docname:
            if not frappe.has_permission(doctype, "write", docname) and not frappe.has_permission(doctype, "cancel", docname):
                raise frappe.PermissionError(f"عذراً، لا تملك الصلاحية الكافية لتنفيذ هذا الإجراء على المستند {docname}")

    clean_args = {}
    try:
        if args:
            serialized = json.dumps(args)
            clean_args = json.loads(serialized)
    except Exception:
        clean_args = args

    try:
        result = func(**clean_args)
        return result
    except Exception as e:
        frappe.log_error(
            title=f"ERP AI Executor Error ({name})",
            message=frappe.get_traceback()
        )
        raise e