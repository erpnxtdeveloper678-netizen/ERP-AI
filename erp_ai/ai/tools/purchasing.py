"""
Purchasing tools - ERPNext's Buying module (Purchase Order, Purchase Receipt,
Supplier). Mirrors the inventory.py / finance.py pattern.

Every tool here is registered with providers=["claude"] - none of them are
exposed to the Gemini provider, and nothing in this file changes the
behavior of any existing tool.

Same security model as the rest of tools/: the AI model is an untrusted
caller acting as frappe.session.user, every doctype/fieldname is validated
via tools/_security.py, and every action goes through frappe's normal
has_permission() checks - no ignore_permissions, no raw SQL. Where ERPNext
already ships a correct "make this next document" helper (e.g. building a
Purchase Receipt from a Purchase Order), we reuse it instead of
hand-assembling the child table ourselves - the same approach already used
in finance.py's create_payment_entry - since ERPNext's own helper already
gets the accounts/rates/quantities right.
"""

import json
import frappe
from erp_ai.ai.decorators import ai_tool
from erp_ai.ai.tools._security import (
    validate_doctype,
    check_permission,
    get_writable_fieldnames,
    resolve_document_name,
)


@ai_tool(
    name="get_pending_purchase_orders",
    description=(
        "List submitted Purchase Orders that are not yet fully received "
        "and/or not yet fully billed - i.e. purchases still 'in flight'. "
        "Optionally filter to one supplier."
    ),
    parameters={
        "supplier": {"type": "string", "description": "Optional. Exact supplier ID or name/part of it - resolved automatically."},
        "limit": {"type": "integer", "description": "Max rows, capped at 100. Default 50."},
    },
    providers=["claude"],
)
def get_pending_purchase_orders(supplier=None, limit=50, **kwargs):
    validate_doctype("Purchase Order")
    check_permission("Purchase Order", "read")

    limit = max(1, min(int(limit or 50), 100))

    filters = [
        ["docstatus", "=", 1],
        ["status", "not in", ["Closed", "Cancelled", "Completed"]],
    ]
    if supplier:
        supplier = resolve_document_name("Supplier", supplier, "supplier_name")
        filters.append(["supplier", "=", supplier])

    rows = frappe.get_list(
        "Purchase Order",
        filters=filters,
        fields=["name", "supplier", "transaction_date", "schedule_date", "grand_total", "per_received", "per_billed", "status"],
        order_by="schedule_date asc",
        limit_page_length=limit,
    )
    return {"supplier": supplier, "pending_orders": rows}


@ai_tool(
    name="get_supplier_summary",
    description=(
        "Get a full picture of one supplier: basic info, total unpaid "
        "(outstanding) Purchase Invoices, and their most recent Purchase Orders."
    ),
    parameters={"supplier": {"type": "string", "required": True, "description": "Exact ID or name/part of it - resolved automatically."}},
    providers=["claude"],
)
def get_supplier_summary(supplier, **kwargs):
    validate_doctype("Supplier")
    supplier = resolve_document_name("Supplier", supplier, "supplier_name")
    check_permission("Supplier", "read", doc=supplier)

    supplier_doc = frappe.get_doc("Supplier", supplier)
    info = {
        "name": supplier_doc.name,
        "supplier_name": supplier_doc.supplier_name,
        "supplier_group": getattr(supplier_doc, "supplier_group", None),
        "country": getattr(supplier_doc, "country", None),
        "disabled": getattr(supplier_doc, "disabled", 0),
    }

    outstanding_total = 0
    recent_invoices = []
    if frappe.db.exists("DocType", "Purchase Invoice") and frappe.has_permission("Purchase Invoice", "read"):
        invoices = frappe.get_list(
            "Purchase Invoice",
            filters=[["supplier", "=", supplier], ["docstatus", "=", 1]],
            fields=["name", "posting_date", "grand_total", "outstanding_amount", "status"],
            order_by="posting_date desc",
            limit_page_length=5,
        )
        recent_invoices = invoices
        outstanding_total = sum(float(i.outstanding_amount or 0) for i in invoices)

    recent_orders = []
    if frappe.db.exists("DocType", "Purchase Order") and frappe.has_permission("Purchase Order", "read"):
        recent_orders = frappe.get_list(
            "Purchase Order",
            filters={"supplier": supplier, "docstatus": 1},
            fields=["name", "transaction_date", "grand_total", "status"],
            order_by="transaction_date desc",
            limit_page_length=5,
        )

    return {
        "supplier": info,
        "outstanding_total_from_last_5_invoices": outstanding_total,
        "recent_invoices": recent_invoices,
        "recent_orders": recent_orders,
    }


@ai_tool(
    name="create_purchase_order",
    description=(
        "Create a Purchase Order for a supplier. Inserted as a DRAFT unless "
        "`submit` is explicitly true - always confirm the items, quantities "
        "and rates with the user before setting submit=true."
    ),
    parameters={
        "supplier": {"type": "string", "required": True, "description": "Exact ID or name/part of it - resolved automatically."},
        "items": {"type": "array", "required": True, "description": "List of {item_code, qty, rate?, schedule_date?}."},
        "schedule_date": {"type": "string", "description": "Default delivery date (YYYY-MM-DD) for rows that don't specify their own."},
        "submit": {"type": "boolean", "description": "Submit immediately instead of leaving as draft. Default false."},
    },
    providers=["claude"],
)
def create_purchase_order(supplier, items, schedule_date=None, submit=False, **kwargs):
    validate_doctype("Purchase Order")
    check_permission("Purchase Order", "create")
    supplier = resolve_document_name("Supplier", supplier, "supplier_name")

    if isinstance(items, str):
        try:
            items = json.loads(items)
        except Exception:
            frappe.throw("`items` must be a list of {item_code, qty, ...} objects.")
    if not isinstance(items, list) or not items:
        frappe.throw("`items` must be a non-empty list.")

    validate_doctype("Purchase Order Item")
    allowed_row_fields = get_writable_fieldnames("Purchase Order Item")

    doc = frappe.new_doc("Purchase Order")
    doc.supplier = supplier
    if schedule_date:
        doc.schedule_date = schedule_date

    for row in items:
        if not isinstance(row, dict) or not row.get("item_code"):
            frappe.throw("Every item row needs at least an `item_code`.")
        clean_row = {k: v for k, v in row.items() if k in allowed_row_fields}
        if not clean_row.get("schedule_date") and schedule_date:
            clean_row["schedule_date"] = schedule_date
        doc.append("items", clean_row)

    doc.insert()

    if submit:
        check_permission("Purchase Order", "submit", doc=doc.name)
        doc.submit()

    return {"status": "success", "doctype": "Purchase Order", "name": doc.name, "docstatus": doc.docstatus}


@ai_tool(
    name="create_purchase_receipt",
    description=(
        "Receive stock against an existing SUBMITTED Purchase Order - the "
        "same as clicking 'Get Items From > Purchase Order' on a new "
        "Purchase Receipt. Built using ERPNext's own mapping so quantities, "
        "rates and warehouses default correctly. Inserted as a DRAFT unless "
        "`submit` is explicitly true."
    ),
    parameters={
        "purchase_order": {"type": "string", "required": True},
        "submit": {"type": "boolean", "description": "Submit immediately instead of leaving as draft. Default false."},
    },
    providers=["claude"],
)
def create_purchase_receipt(purchase_order, submit=False, **kwargs):
    validate_doctype("Purchase Order")
    check_permission("Purchase Order", "read", doc=purchase_order)
    validate_doctype("Purchase Receipt")
    check_permission("Purchase Receipt", "create")

    po = frappe.get_doc("Purchase Order", purchase_order)
    if po.docstatus != 1:
        frappe.throw(f"Purchase Order '{purchase_order}' must be submitted before a receipt can be created against it.")

    try:
        from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
    except ImportError:
        frappe.throw("The erpnext app is not installed on this site.")

    pr = make_purchase_receipt(purchase_order)
    pr.insert()

    if submit:
        check_permission("Purchase Receipt", "submit", doc=pr.name)
        pr.submit()

    return {
        "status": "success", "doctype": "Purchase Receipt", "name": pr.name,
        "against": f"Purchase Order {purchase_order}", "docstatus": pr.docstatus,
    }
    