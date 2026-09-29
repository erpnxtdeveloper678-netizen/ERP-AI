"""
CRM / customer-follow-up tools (ERPNext's Selling & CRM modules: Customer,
Opportunity, Communication).

Every tool here is registered with providers=["claude"] (see decorators.py /
registry.py) - none of them are exposed to the Gemini provider.

Follows the exact same security model as tools/documents.py: the AI model is
an untrusted caller acting as frappe.session.user, every doctype/fieldname is
validated with the shared helpers in tools/_security.py, and every action
goes through frappe's normal has_permission() checks - nothing here uses
ignore_permissions or raw SQL.
"""

import frappe
from erp_ai.ai.decorators import ai_tool
from erp_ai.ai.tools._security import validate_doctype, check_permission, resolve_document_name
from erp_ai.ai.tools.analytics import analyze_data


@ai_tool(
    name="get_customer_360",
    description=(
        "Get a single-call summary of a Customer: their basic details, "
        "total and outstanding Sales Invoice amounts, count of open "
        "Opportunities, and their most recent logged interaction "
        "(Communication). Use this instead of several separate "
        "list_documents calls when the user asks for an overview of one "
        "customer."
    ),
    parameters={"customer": {"type": "string", "required": True}},
    providers=["claude"],
)
def get_customer_360(customer, **kwargs):
    validate_doctype("Customer")
    customer = resolve_document_name("Customer", customer, "customer_name")
    check_permission("Customer", "read", doc=customer)

    customer_doc = frappe.get_list(
        "Customer",
        filters={"name": customer},
        fields=["name", "customer_name", "customer_group", "territory", "disabled"],
        limit_page_length=1,
    )
    summary = {"customer": customer_doc[0] if customer_doc else {"name": customer}}

    if frappe.db.exists("DocType", "Sales Invoice") and frappe.has_permission("Sales Invoice", "read"):
        invoiced = analyze_data(
            "Sales Invoice", "sum", field="grand_total",
            filters={"customer": customer, "docstatus": 1},
        )
        outstanding = analyze_data(
            "Sales Invoice", "sum", field="outstanding_amount",
            filters={"customer": customer, "docstatus": 1},
        )
        summary["total_invoiced"] = invoiced.get("value", 0)
        summary["total_outstanding"] = outstanding.get("value", 0)

    if frappe.db.exists("DocType", "Opportunity") and frappe.has_permission("Opportunity", "read"):
        open_opps = analyze_data(
            "Opportunity", "count",
            filters={"party_name": customer, "status": "Open"},
        )
        summary["open_opportunities"] = open_opps.get("value", 0)

    if frappe.db.exists("DocType", "Communication") and frappe.has_permission("Communication", "read"):
        last_comm = frappe.get_list(
            "Communication",
            filters={"reference_doctype": "Customer", "reference_name": customer},
            fields=["subject", "communication_date", "sender"],
            order_by="communication_date desc",
            limit_page_length=1,
        )
        summary["last_interaction"] = last_comm[0] if last_comm else None

    return summary


@ai_tool(
    name="get_sales_pipeline",
    description=(
        "Overview of open Opportunities grouped by sales stage (or another "
        "field), with a count and total opportunity_amount per group. "
        "Answers 'what does our pipeline look like' style questions."
    ),
    parameters={
        "group_by": {"type": "string", "description": "Field to group by. Default 'sales_stage'."},
        "limit": {"type": "integer", "description": "Capped at 50. Default 20."},
    },
    providers=["claude"],
)
def get_sales_pipeline(group_by="sales_stage", limit=20, **kwargs):
    validate_doctype("Opportunity")
    check_permission("Opportunity", "read")

    limit = max(1, min(int(limit or 20), 50))

    counts = analyze_data(
        "Opportunity", "group", group_by=group_by or "sales_stage",
        aggregate="count", filters={"status": "Open"}, limit=limit,
    )
    totals = analyze_data(
        "Opportunity", "group", group_by=group_by or "sales_stage",
        aggregate="sum", field="opportunity_amount", filters={"status": "Open"}, limit=limit,
    )

    total_by_key = {row["group_field"]: row["value"] for row in totals.get("data", [])}
    stages = [
        {
            "group": row["group_field"],
            "count": row["value"],
            "total_opportunity_amount": total_by_key.get(row["group_field"], 0),
        }
        for row in counts.get("data", [])
    ]
    return {"group_by": group_by or "sales_stage", "stages": stages}


@ai_tool(
    name="create_follow_up_task",
    description=(
        "Assign a follow-up task/reminder on a CRM record (e.g. a Lead or "
        "Opportunity) to a user - the same as the 'Assign To' action, with "
        "wording aimed at CRM follow-ups. Creates a ToDo and notifies the "
        "assignee. This is an alias over the same mechanism as "
        "assign_document, kept separate because it's the more natural tool "
        "name for 'remind me / remind X to follow up with this lead'."
    ),
    parameters={
        "reference_doctype": {"type": "string", "required": True, "description": "e.g. 'Lead', 'Opportunity', 'Customer'."},
        "reference_name": {"type": "string", "required": True},
        "assign_to": {"type": "string", "description": "User email. Defaults to the current user."},
        "description": {"type": "string", "description": "What to follow up about."},
        "due_date": {"type": "string", "description": "YYYY-MM-DD. Optional."},
    },
    providers=["claude"],
)
def create_follow_up_task(reference_doctype, reference_name, assign_to=None, description=None, due_date=None, **kwargs):
    validate_doctype(reference_doctype)
    check_permission(reference_doctype, "read", doc=reference_name)

    assignee = assign_to or frappe.session.user
    if not frappe.db.exists("User", assignee):
        frappe.throw(f"Unknown user: '{assignee}'.")

    from frappe.desk.form.assign_to import add as assign_to_add

    result = assign_to_add({
        "doctype": reference_doctype,
        "name": reference_name,
        "assign_to": [assignee],
        "description": description or f"Follow up on {reference_doctype} {reference_name}",
        "date": due_date,
    })
    todo_name = result[0].name if result else None
    return {
        "status": "success", "reference_doctype": reference_doctype, "reference_name": reference_name,
        "assigned_to": assignee, "todo": todo_name,
    }
    