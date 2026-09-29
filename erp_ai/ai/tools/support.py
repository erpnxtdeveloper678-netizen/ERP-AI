"""
Support / Helpdesk tools - Frappe Helpdesk's HD Ticket doctype.

This is a SEPARATE app from erpnext (frappe/helpdesk) and may not be
installed on every site. That's fine: validate_doctype() throws a clear
"Unknown DocType" error (caught by executor.py, returned to the model as a
normal tool error) rather than failing obscurely, exactly like every other
tool here when its underlying app isn't installed - see the note at the top
of tools/inventory.py.

Every tool here is registered with providers=["claude"]. Same security
model as the rest of tools/.
"""

import frappe
from erp_ai.ai.decorators import ai_tool
from erp_ai.ai.tools._security import validate_doctype, check_permission, resolve_document_name


@ai_tool(
    name="get_open_tickets",
    description="List open (not yet closed/resolved) support tickets, optionally filtered by customer or priority.",
    parameters={
        "customer": {"type": "string", "description": "Optional. Exact ID or name/part of it - resolved automatically, if this site links tickets to a Customer."},
        "priority": {"type": "string", "description": "Optional. e.g. 'Low', 'Medium', 'High', 'Urgent'."},
        "limit": {"type": "integer", "description": "Max rows, capped at 100. Default 50."},
    },
    providers=["claude"],
)
def get_open_tickets(customer=None, priority=None, limit=50, **kwargs):
    validate_doctype("HD Ticket")
    check_permission("HD Ticket", "read")

    limit = max(1, min(int(limit or 50), 100))
    filters = [["status", "not in", ["Closed", "Resolved"]]]

    if customer:
        validate_doctype("Customer")
        customer = resolve_document_name("Customer", customer, "customer_name")
        filters.append(["customer", "=", customer])
    if priority:
        filters.append(["priority", "=", priority])

    rows = frappe.get_list(
        "HD Ticket",
        filters=filters,
        fields=["name", "subject", "status", "priority", "raised_by", "customer", "creation"],
        order_by="creation desc",
        limit_page_length=limit,
    )
    return {"open_tickets": rows}


@ai_tool(
    name="get_ticket_details",
    description="Get the full details of one support ticket by its ID.",
    parameters={"ticket": {"type": "string", "required": True}},
    providers=["claude"],
)
def get_ticket_details(ticket, **kwargs):
    validate_doctype("HD Ticket")
    check_permission("HD Ticket", "read", doc=ticket)

    if not frappe.db.exists("HD Ticket", ticket):
        frappe.throw(f"Unknown HD Ticket: '{ticket}'.")

    doc = frappe.get_doc("HD Ticket", ticket)
    return {
        "name": doc.name,
        "subject": doc.subject,
        "description": getattr(doc, "description", None),
        "status": doc.status,
        "priority": getattr(doc, "priority", None),
        "raised_by": getattr(doc, "raised_by", None),
        "customer": getattr(doc, "customer", None),
        "creation": str(doc.creation),
    }


@ai_tool(
    name="create_ticket",
    description="Create a new support ticket.",
    parameters={
        "subject": {"type": "string", "required": True},
        "description": {"type": "string", "required": True},
        "raised_by": {"type": "string", "description": "Optional. Requester's email. Defaults to the current user."},
        "priority": {"type": "string", "description": "Optional. e.g. 'Low', 'Medium', 'High', 'Urgent'."},
        "customer": {"type": "string", "description": "Optional. Exact ID or name/part of it - resolved automatically."},
    },
    providers=["claude"],
)
def create_ticket(subject, description, raised_by=None, priority=None, customer=None, **kwargs):
    validate_doctype("HD Ticket")
    check_permission("HD Ticket", "create")

    doc = frappe.new_doc("HD Ticket")
    doc.subject = subject
    doc.description = description
    doc.raised_by = raised_by or frappe.session.user
    if priority:
        doc.priority = priority
    if customer:
        validate_doctype("Customer")
        doc.customer = resolve_document_name("Customer", customer, "customer_name")

    doc.insert()

    return {"status": "success", "doctype": "HD Ticket", "name": doc.name, "status_field": doc.status}


@ai_tool(
    name="update_ticket_status",
    description="Change a support ticket's status (e.g. 'Replied', 'Resolved', 'Closed').",
    parameters={
        "ticket": {"type": "string", "required": True},
        "status": {"type": "string", "required": True},
    },
    providers=["claude"],
)
def update_ticket_status(ticket, status, **kwargs):
    validate_doctype("HD Ticket")
    check_permission("HD Ticket", "write", doc=ticket)

    if not frappe.db.exists("HD Ticket", ticket):
        frappe.throw(f"Unknown HD Ticket: '{ticket}'.")

    doc = frappe.get_doc("HD Ticket", ticket)
    doc.status = status
    doc.save()

    return {"status": "success", "doctype": "HD Ticket", "name": doc.name, "new_status": doc.status}
    