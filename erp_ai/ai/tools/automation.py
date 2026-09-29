"""
Reminders & "what needs my attention" tools.

Every tool here is registered with providers=["claude"] (see decorators.py /
registry.py) - none of them are exposed to the Gemini provider.

Deliberately narrow scope: this file does NOT include a generic
"create_notification_rule"-style tool. ERPNext's core Notification doctype
lets its `condition` field be a Python expression that Frappe evaluates
against the document at runtime - handing the AI model a way to author that
string would effectively be a code-execution primitive on the server, the
same class of risk that execute_sql was removed for elsewhere in this app
(see documents.py). Everything below only ever creates a plain ToDo, which
has no such eval surface.

Follows the exact same security model as tools/documents.py: the AI model is
an untrusted caller acting as frappe.session.user, every doctype/fieldname is
validated with the shared helpers in tools/_security.py, and every action
goes through frappe's normal has_permission() checks - nothing here uses
ignore_permissions or raw SQL.
"""

import frappe
from erp_ai.ai.decorators import ai_tool
from erp_ai.ai.tools._security import validate_doctype, check_permission


@ai_tool(
    name="get_overdue_items",
    description=(
        "What needs the current user's attention right now: their own open "
        "ToDos/assignments past their due date, plus (if the Accounts "
        "module is installed and readable) submitted Sales Invoices that "
        "are overdue and unpaid. Permission-filtered exactly like the desk "
        "UI - never returns records the current user can't see."
    ),
    parameters={
        "limit": {"type": "integer", "description": "Max rows per category, capped at 100. Default 20."},
    },
    providers=["claude"],
)
def get_overdue_items(limit=20, **kwargs):
    limit = max(1, min(int(limit or 20), 100))
    today = frappe.utils.today()
    result = {}

    if frappe.db.exists("DocType", "ToDo") and frappe.has_permission("ToDo", "read"):
        todos = frappe.get_list(
            "ToDo",
            filters={
                "allocated_to": frappe.session.user, "status": "Open",
                "date": ["<", today],
            },
            fields=["name", "reference_type", "reference_name", "description", "date", "priority"],
            order_by="date asc",
            limit_page_length=limit,
        )
        result["overdue_todos"] = todos

    if frappe.db.exists("DocType", "Sales Invoice") and frappe.has_permission("Sales Invoice", "read"):
        invoices = frappe.get_list(
            "Sales Invoice",
            filters={"docstatus": 1, "outstanding_amount": [">", 0], "due_date": ["<", today]},
            fields=["name", "customer", "due_date", "outstanding_amount", "currency"],
            order_by="due_date asc",
            limit_page_length=limit,
        )
        result["overdue_invoices"] = invoices

    return result


@ai_tool(
    name="schedule_reminder",
    description=(
        "Create a standalone reminder (a ToDo) for a user, optionally linked "
        "to a document. Unlike create_follow_up_task/assign_document, no "
        "reference document is required - use this for freeform reminders "
        "('remind me to call the supplier tomorrow')."
    ),
    parameters={
        "description": {"type": "string", "required": True},
        "remind_at": {"type": "string", "required": True, "description": "YYYY-MM-DD"},
        "assign_to": {"type": "string", "description": "User email. Defaults to the current user."},
        "reference_doctype": {"type": "string", "description": "Optional linked document's DocType."},
        "reference_name": {"type": "string", "description": "Optional linked document's name."},
        "priority": {"type": "string", "description": "Low | Medium | High. Default Medium."},
    },
    providers=["claude"],
)
def schedule_reminder(description, remind_at, assign_to=None, reference_doctype=None,
                       reference_name=None, priority="Medium", **kwargs):
    validate_doctype("ToDo")
    check_permission("ToDo", "create")

    assignee = assign_to or frappe.session.user
    if not frappe.db.exists("User", assignee):
        frappe.throw(f"Unknown user: '{assignee}'.")

    if reference_doctype:
        validate_doctype(reference_doctype)
        if not reference_name:
            frappe.throw("`reference_name` is required when `reference_doctype` is given.")
        check_permission(reference_doctype, "read", doc=reference_name)

    doc = frappe.new_doc("ToDo")
    doc.description = description
    doc.date = remind_at
    doc.allocated_to = assignee
    doc.priority = priority or "Medium"
    if reference_doctype:
        doc.reference_type = reference_doctype
        doc.reference_name = reference_name
    doc.insert()

    return {
        "status": "success", "doctype": "ToDo", "name": doc.name,
        "assigned_to": assignee, "remind_at": remind_at,
    }