import json
import frappe
from erp_ai.ai.registry import get_tool

# Action keywords that indicate a mutating/destructive operation. Used to
# apply an extra permission pre-check before even calling the tool function.
MUTATING_ACTIONS = ["cancel", "submit", "update", "delete", "create"]


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

    # Extra permission pre-check for mutating operations. This checks the
    # ACTUAL ACTION being requested (from args["action"], e.g. "cancel") —
    # not the tool's own name — since a generic tool like
    # "manage_erp_document" never contains those words in its name and the
    # check would otherwise silently never fire. Individual tool functions
    # (e.g. manage_erp_document) still do their own permission check too;
    # this is a defense-in-depth layer, not a replacement for it.
    requested_action = str(args.get("action", "")).lower()
    is_mutating = requested_action in MUTATING_ACTIONS or any(
        action in name.lower() for action in MUTATING_ACTIONS
    )

    if is_mutating:
        docname = args.get("name") or args.get("docname")
        doctype = args.get("doctype")

        if doctype and docname:
            perm_type = "cancel" if requested_action == "cancel" else "write"
            if not frappe.has_permission(doctype, perm_type, docname) and not frappe.has_permission(doctype, "cancel", docname):
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
    except TypeError as e:
        # Usually means the model passed an argument the function doesn't
        # accept, or is missing a required one — surface a clear message
        # instead of a raw Python TypeError string reaching the user.
        frappe.log_error(
            title=f"ERP AI Executor Argument Error ({name})",
            message=f"{frappe.get_traceback()}\n\nArgs received: {clean_args}"
        )
        raise ValueError(f"Invalid arguments for tool '{name}': {e}")
    except Exception as e:
        frappe.log_error(
            title=f"ERP AI Executor Error ({name})",
            message=frappe.get_traceback()
        )
        raise e