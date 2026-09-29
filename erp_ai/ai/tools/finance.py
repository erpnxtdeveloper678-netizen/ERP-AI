"""
Finance / accounting tools (ERPNext's Accounts module: Sales Invoice,
Purchase Invoice, Payment Entry).

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

_PARTY_DOCTYPE = {"Customer": "Sales Invoice", "Supplier": "Purchase Invoice"}
_PARTY_FIELD = {"Customer": "customer", "Supplier": "supplier"}
_PARTY_NAME_FIELD = {"Customer": "customer_name", "Supplier": "supplier_name"}


@ai_tool(
    name="get_outstanding_invoices",
    description=(
        "List submitted, not-fully-paid invoices - Sales Invoices owed by "
        "customers (party_type='Customer') or Purchase Invoices owed to "
        "suppliers (party_type='Supplier'). Optionally scoped to a single "
        "party (customer/supplier name)."
    ),
    parameters={
        "party_type": {"type": "string", "required": True, "description": "'Customer' or 'Supplier'."},
        "party": {"type": "string", "description": "Optional. A specific customer/supplier name."},
        "limit": {"type": "integer", "description": "Capped at 200. Default 50."},
    },
    providers=["claude"],
)
def get_outstanding_invoices(party_type, party=None, limit=50, **kwargs):
    if party_type not in _PARTY_DOCTYPE:
        frappe.throw("`party_type` must be 'Customer' or 'Supplier'.")

    doctype = _PARTY_DOCTYPE[party_type]
    validate_doctype(doctype)
    check_permission(doctype, "read")

    if party:
        party = resolve_document_name(party_type, party, _PARTY_NAME_FIELD[party_type])

    limit = max(1, min(int(limit or 50), 200))

    filters = {"docstatus": 1, "outstanding_amount": [">", 0]}
    if party:
        filters[_PARTY_FIELD[party_type]] = party

    rows = frappe.get_list(
        doctype,
        filters=filters,
        fields=[
            "name", _PARTY_FIELD[party_type], "posting_date", "due_date",
            "grand_total", "outstanding_amount", "currency",
        ],
        order_by="due_date asc",
        limit_page_length=limit,
    )
    total_outstanding = sum(float(r.outstanding_amount or 0) for r in rows)
    return {
        "party_type": party_type, "party": party, "doctype": doctype,
        "count": len(rows), "total_outstanding": total_outstanding, "invoices": rows,
    }


@ai_tool(
    name="get_aging_report",
    description=(
        "Bucket outstanding invoices for a party type (Customer receivables "
        "or Supplier payables) into age ranges - 0-30, 31-60, 61-90, and "
        "90+ days overdue - based on `due_date` vs today. Answers 'how much "
        "is overdue and by how long' style questions."
    ),
    parameters={
        "party_type": {"type": "string", "required": True, "description": "'Customer' or 'Supplier'."},
        "party": {"type": "string", "description": "Optional. A specific customer/supplier name."},
    },
    providers=["claude"],
)
def get_aging_report(party_type, party=None, **kwargs):
    if party_type not in _PARTY_DOCTYPE:
        frappe.throw("`party_type` must be 'Customer' or 'Supplier'.")

    doctype = _PARTY_DOCTYPE[party_type]
    validate_doctype(doctype)
    check_permission(doctype, "read")

    if party:
        party = resolve_document_name(party_type, party, _PARTY_NAME_FIELD[party_type])

    filters = {"docstatus": 1, "outstanding_amount": [">", 0]}
    if party:
        filters[_PARTY_FIELD[party_type]] = party

    rows = frappe.get_list(
        doctype,
        filters=filters,
        fields=["name", _PARTY_FIELD[party_type], "due_date", "outstanding_amount"],
        limit_page_length=1000,
    )

    today = frappe.utils.getdate()
    buckets = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0, "not_yet_due": 0.0}
    for r in rows:
        amount = float(r.outstanding_amount or 0)
        due = frappe.utils.getdate(r.due_date) if r.due_date else None
        if not due or due >= today:
            buckets["not_yet_due"] += amount
            continue
        days_overdue = (today - due).days
        if days_overdue <= 30:
            buckets["0-30"] += amount
        elif days_overdue <= 60:
            buckets["31-60"] += amount
        elif days_overdue <= 90:
            buckets["61-90"] += amount
        else:
            buckets["90+"] += amount

    return {
        "party_type": party_type, "party": party, "as_on": today.isoformat(),
        "total_outstanding": sum(buckets.values()), "buckets": buckets,
    }


@ai_tool(
    name="create_payment_entry",
    description=(
        "Create a Payment Entry against a specific submitted Sales/Purchase "
        "Invoice, prefilled the same way clicking 'Create -> Payment' on the "
        "invoice does (correct party, accounts, and outstanding amount). "
        "Inserted as a DRAFT - not automatically submitted; use "
        "submit_document once the user confirms the amount."
    ),
    parameters={
        "invoice_doctype": {"type": "string", "required": True, "description": "'Sales Invoice' or 'Purchase Invoice'."},
        "invoice_name": {"type": "string", "required": True},
        "paid_amount": {"type": "number", "description": "Optional override. Defaults to the full outstanding amount."},
    },
    providers=["claude"],
)
def create_payment_entry(invoice_doctype, invoice_name, paid_amount=None, **kwargs):
    if invoice_doctype not in ("Sales Invoice", "Purchase Invoice"):
        frappe.throw("`invoice_doctype` must be 'Sales Invoice' or 'Purchase Invoice'.")

    validate_doctype(invoice_doctype)
    check_permission(invoice_doctype, "read", doc=invoice_name)
    validate_doctype("Payment Entry")
    check_permission("Payment Entry", "create")

    invoice = frappe.get_doc(invoice_doctype, invoice_name)
    if invoice.docstatus != 1:
        frappe.throw(f"{invoice_doctype} '{invoice_name}' must be submitted before a payment can be created against it.")

    try:
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    except ImportError:
        frappe.throw("The erpnext app is not installed on this site.")

    pe = get_payment_entry(invoice_doctype, invoice_name)
    if paid_amount is not None:
        pe.paid_amount = paid_amount
        pe.received_amount = paid_amount
        if pe.references:
            pe.references[0].allocated_amount = paid_amount

    pe.insert()
    return {
        "status": "success", "doctype": "Payment Entry", "name": pe.name,
        "against": f"{invoice_doctype} {invoice_name}", "paid_amount": pe.paid_amount,
    }


@ai_tool(
    name="reconcile_payment",
    description=(
        "Allocate an existing DRAFT Payment Entry against a submitted "
        "invoice - adds a row to the payment's 'references' table linking "
        "it to the invoice for the given amount, the same as the "
        "reconciliation table on the Payment Entry form. The Payment Entry "
        "must not already be submitted."
    ),
    parameters={
        "payment_entry": {"type": "string", "required": True},
        "invoice_doctype": {"type": "string", "required": True, "description": "'Sales Invoice' or 'Purchase Invoice'."},
        "invoice_name": {"type": "string", "required": True},
        "allocated_amount": {"type": "number", "required": True},
    },
    providers=["claude"],
)
def reconcile_payment(payment_entry, invoice_doctype, invoice_name, allocated_amount, **kwargs):
    if invoice_doctype not in ("Sales Invoice", "Purchase Invoice"):
        frappe.throw("`invoice_doctype` must be 'Sales Invoice' or 'Purchase Invoice'.")

    validate_doctype("Payment Entry")
    check_permission("Payment Entry", "write", doc=payment_entry)
    validate_doctype(invoice_doctype)
    check_permission(invoice_doctype, "read", doc=invoice_name)

    pe = frappe.get_doc("Payment Entry", payment_entry)
    if pe.docstatus != 0:
        frappe.throw("Only a draft Payment Entry can be reconciled/edited.")

    invoice = frappe.get_doc(invoice_doctype, invoice_name)
    if invoice.docstatus != 1:
        frappe.throw(f"{invoice_doctype} '{invoice_name}' must be submitted.")

    pe.append("references", {
        "reference_doctype": invoice_doctype,
        "reference_name": invoice_name,
        "total_amount": invoice.grand_total,
        "outstanding_amount": invoice.outstanding_amount,
        "allocated_amount": allocated_amount,
    })
    pe.save()
    return {
        "status": "success", "doctype": "Payment Entry", "name": pe.name,
        "reconciled_with": f"{invoice_doctype} {invoice_name}", "allocated_amount": allocated_amount,
    }
    