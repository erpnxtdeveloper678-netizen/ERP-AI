"""
Extra tools that extend the assistant's reach beyond plain CRUD + analytics:
cross-document actions that mirror common buttons/flows in the ERPNext desk UI
(Connections, Assign To, workflow approvals, the "Create" mapping dropdown,
Print, Email).

Every tool here is registered with providers=["claude"] (see decorators.py /
registry.py) - none of them are exposed to the Gemini provider.

Follows the exact same security model as tools/documents.py: the AI model is
an untrusted caller acting as frappe.session.user, every doctype/fieldname is
validated, and every action goes through frappe's normal has_permission()
checks - nothing here uses ignore_permissions or raw SQL.
"""

import json
import frappe
from erp_ai.ai.decorators import ai_tool
from erp_ai.ai.tools._security import (
    validate_doctype,
    check_permission,
    get_writable_fieldnames,
    parse_json_object,
)


@ai_tool(
    name="get_linked_documents",
    description=(
        "Find all records across ERPNext linked to a specific document via its Link "
        "fields - e.g. every Sales Invoice, Delivery Note and Payment Entry connected "
        "to a Customer. Mirrors the 'Connections' tab on the document's form. Only "
        "linked doctypes the current user has at least read permission on are "
        "returned, capped at 20 rows per linked doctype."
    ),
    parameters={
        "doctype": {"type": "string", "required": True},
        "name": {"type": "string", "required": True},
    },
    providers=["claude"],
)
def get_linked_documents(doctype, name, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "read", doc=name)

    from frappe.desk.form.linked_with import get_linked_docs, get_linked_doctypes

    linkinfo = get_linked_doctypes(doctype)
    if not linkinfo:
        return {"doctype": doctype, "name": name, "linked": {}}

    all_linked = get_linked_docs(doctype, name, linkinfo=linkinfo) or {}

    results = {}
    for linked_doctype, rows in all_linked.items():
        if not rows or not frappe.has_permission(linked_doctype, "read"):
            continue
        results[linked_doctype] = rows[:20]

    return {"doctype": doctype, "name": name, "linked": results}


# Curated allowlist of ERPNext's native "Create ->" document-mapping flows.
# Deliberately NOT dynamic/arbitrary - only these exact, known-safe pairs can
# be triggered. If erpnext isn't installed, or a pair isn't in this list,
# the tool refuses with a clear message instead of guessing a dotted path.
_MAKE_FUNCTIONS = {
    ("Quotation", "Sales Order"): "erpnext.selling.doctype.quotation.quotation.make_sales_order",
    ("Sales Order", "Sales Invoice"): "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
    ("Sales Order", "Delivery Note"): "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
    ("Delivery Note", "Sales Invoice"): "erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice",
    ("Purchase Order", "Purchase Invoice"): "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice",
    ("Purchase Order", "Purchase Receipt"): "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt",
    ("Purchase Receipt", "Purchase Invoice"): "erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice",
    ("Material Request", "Purchase Order"): "erpnext.stock.doctype.material_request.material_request.make_purchase_order",
    ("Lead", "Customer"): "erpnext.crm.doctype.lead.lead.make_customer",
    ("Lead", "Opportunity"): "erpnext.crm.doctype.lead.lead.make_opportunity",
    ("Opportunity", "Quotation"): "erpnext.crm.doctype.opportunity.opportunity.make_quotation",
}


@ai_tool(
    name="create_linked_document",
    description=(
        "Create a new document by mapping it from an existing one - the same as "
        "clicking 'Create' on a document's form in ERPNext (e.g. making a Sales "
        "Invoice from a Sales Order, or a Customer from a Lead). Only the specific "
        "source->target pairs ERPNext supports natively are allowed; calling this "
        "with an unsupported pair returns a clear error listing the valid targets "
        "for that source doctype instead of guessing. Requires the erpnext app to "
        "be installed on this site. The result is inserted as a DRAFT - it is not "
        "automatically submitted."
    ),
    parameters={
        "source_doctype": {"type": "string", "required": True},
        "source_name": {"type": "string", "required": True},
        "target_doctype": {"type": "string", "required": True},
    },
    providers=["claude"],
)
def create_linked_document(source_doctype, source_name, target_doctype, **kwargs):
    validate_doctype(source_doctype)
    validate_doctype(target_doctype)
    check_permission(source_doctype, "read", doc=source_name)
    check_permission(target_doctype, "create")

    dotted_path = _MAKE_FUNCTIONS.get((source_doctype, target_doctype))
    if not dotted_path:
        available = [t for (s, t) in _MAKE_FUNCTIONS if s == source_doctype]
        frappe.throw(
            f"Cannot create a {target_doctype} from a {source_doctype} directly. "
            + (f"Supported targets from {source_doctype}: {', '.join(available)}."
               if available else f"No supported mapping exists from {source_doctype}.")
        )

    try:
        make_fn = frappe.get_attr(dotted_path)
    except Exception:
        frappe.throw(
            "The mapping function for this pair is not available on this site "
            "(the erpnext app may not be installed)."
        )

    mapped = make_fn(source_name)
    doc = mapped if hasattr(mapped, "insert") else frappe.get_doc(mapped)
    doc.insert()

    return {
        "status": "success", "doctype": doc.doctype, "name": doc.name,
        "mapped_from": f"{source_doctype} {source_name}",
    }


@ai_tool(
    name="duplicate_document",
    description=(
        "Create a copy of an existing document as a starting point for a new draft, "
        "optionally overriding some fields on the copy (e.g. duplicate last month's "
        "recurring Sales Order for a new customer)."
    ),
    parameters={
        "doctype": {"type": "string", "required": True},
        "name": {"type": "string", "required": True},
        "overrides": {"type": "object", "description": "Field values to change on the copy."},
    },
    providers=["claude"],
)
def duplicate_document(doctype, name, overrides=None, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "read", doc=name)
    check_permission(doctype, "create")

    source = frappe.get_doc(doctype, name)
    new_doc = frappe.copy_doc(source)

    if overrides:
        overrides = parse_json_object(overrides, "overrides")
        allowed = get_writable_fieldnames(doctype)
        clean = {k: v for k, v in overrides.items() if k in allowed}
        new_doc.update(clean)

    new_doc.insert()
    return {"status": "success", "doctype": doctype, "name": new_doc.name, "duplicated_from": name}


@ai_tool(
    name="assign_document",
    description=(
        "Assign a document to one or more users, the same as the 'Assign To' action "
        "in ERPNext - creates a ToDo and notifies them."
    ),
    parameters={
        "doctype": {"type": "string", "required": True},
        "name": {"type": "string", "required": True},
        "assign_to": {"type": "array", "required": True, "description": "List of user emails/IDs."},
        "description": {"type": "string", "description": "Note explaining the task."},
    },
    providers=["claude"],
)
def assign_document(doctype, name, assign_to, description=None, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "read", doc=name)

    if isinstance(assign_to, str):
        try:
            assign_to = json.loads(assign_to)
        except Exception:
            assign_to = [assign_to]
    if not isinstance(assign_to, list) or not assign_to:
        frappe.throw("`assign_to` must be a non-empty list of user emails.")

    valid_users = [u for u in assign_to if frappe.db.exists("User", u)]
    if not valid_users:
        frappe.throw("None of the given users exist.")

    from frappe.desk.form.assign_to import add as assign_to_add

    assign_to_add({
        "doctype": doctype,
        "name": name,
        "assign_to": valid_users,
        "description": description or f"Please review this {doctype}.",
    })
    return {"status": "success", "doctype": doctype, "name": name, "assigned_to": valid_users}


@ai_tool(
    name="apply_workflow_action",
    description=(
        "Apply a workflow transition action (e.g. 'Approve', 'Reject') on a document "
        "that has a Workflow configured (Leave Application, Expense Claim, custom "
        "approval flows, etc). If unsure of the exact action label for this document, "
        "ask the user - action names are defined per-workflow and vary by site."
    ),
    parameters={
        "doctype": {"type": "string", "required": True},
        "name": {"type": "string", "required": True},
        "action": {"type": "string", "required": True, "description": "Exact workflow action label."},
    },
    providers=["claude"],
)
def apply_workflow_action(doctype, name, action, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "write", doc=name)

    if not frappe.db.exists("Workflow", {"document_type": doctype, "is_active": 1}):
        frappe.throw(f"{doctype} has no active Workflow configured.")

    from frappe.model.workflow import apply_workflow

    doc = frappe.get_doc(doctype, name)
    updated = apply_workflow(doc, action)
    return {
        "status": "success", "doctype": doctype, "name": name, "action": action,
        "new_status": getattr(updated, "workflow_state", None),
    }


@ai_tool(
    name="add_comment",
    description="Add a comment/note to an ERPNext document's timeline.",
    parameters={
        "doctype": {"type": "string", "required": True},
        "name": {"type": "string", "required": True},
        "comment": {"type": "string", "required": True},
    },
    providers=["claude"],
)
def add_comment(doctype, name, comment, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "read", doc=name)

    if not comment or not comment.strip():
        frappe.throw("`comment` cannot be empty.")

    doc = frappe.get_doc(doctype, name)
    c = doc.add_comment("Comment", comment.strip())
    return {"status": "success", "doctype": doctype, "name": name, "comment_name": c.name}


@ai_tool(
    name="global_search",
    description=(
        "Search across every doctype's indexed content for matching text, the same "
        "as the top search bar in ERPNext. Use this when you don't know which "
        "specific DocType a record belongs to. For a targeted search within one "
        "known DocType, use list_documents with filters instead - it's faster and "
        "more precise."
    ),
    parameters={
        "text": {"type": "string", "required": True},
        "limit": {"type": "integer", "description": "Max results, capped at 50. Default 20."},
    },
    providers=["claude"],
)
def global_search(text, limit=20, **kwargs):
    if not text or not text.strip():
        frappe.throw("`text` is required.")
    limit = max(1, min(int(limit or 20), 50))

    from frappe.utils.global_search import search as gs_search

    raw_results = gs_search(text.strip(), start=0, limit=limit * 2) or []

    results = []
    for r in raw_results:
        r_doctype = r.get("doctype") if isinstance(r, dict) else None
        r_name = r.get("name") if isinstance(r, dict) else None
        if r_doctype and r_name and frappe.has_permission(r_doctype, "read", doc=r_name):
            results.append({
                "doctype": r_doctype, "name": r_name,
                "content": (r.get("content") or "")[:200],
            })
        if len(results) >= limit:
            break

    return {"query": text, "results": results}


@ai_tool(
    name="bulk_update_documents",
    description=(
        "Apply the same field changes to multiple existing DRAFT documents of one "
        "DocType at once (e.g. marking several Tasks as 'Completed'). Capped at 50 "
        "documents per call. This is a real, irreversible bulk write, not a preview "
        "- always confirm the exact list of documents and the change with the user "
        "first, and only call this after they explicitly confirm in their next "
        "message."
    ),
    parameters={
        "doctype": {"type": "string", "required": True},
        "names": {"type": "array", "required": True, "description": "Document names to update."},
        "data": {"type": "object", "required": True, "description": "Field values to apply to every document."},
    },
    providers=["claude"],
)
def bulk_update_documents(doctype, names, data, **kwargs):
    validate_doctype(doctype)

    if isinstance(names, str):
        try:
            names = json.loads(names)
        except Exception:
            frappe.throw("`names` must be a list of document names.")
    if not isinstance(names, list) or not names:
        frappe.throw("`names` must be a non-empty list.")
    if len(names) > 50:
        frappe.throw("bulk_update_documents supports at most 50 documents per call.")

    data = parse_json_object(data)
    allowed = get_writable_fieldnames(doctype)
    clean_data = {k: v for k, v in data.items() if k in allowed}
    if not clean_data:
        frappe.throw("None of the given fields in `data` are writable on this DocType.")

    results = []
    for name in names:
        try:
            check_permission(doctype, "write", doc=name)
            doc = frappe.get_doc(doctype, name)
            if doc.docstatus != 0:
                results.append({"name": name, "status": "error", "message": "Not a draft; skipped."})
                continue
            doc.update(clean_data)
            doc.save()
            results.append({"name": name, "status": "success"})
        except Exception as e:
            results.append({"name": name, "status": "error", "message": str(e)})

    return {"doctype": doctype, "updated_fields": list(clean_data.keys()), "results": results}


@ai_tool(
    name="send_document_email",
    description=(
        "Email a document (e.g. a Quotation or Sales Invoice) to a recipient, "
        "attaching its PDF. This sends a REAL email immediately. Always confirm the "
        "exact recipient address and the document with the user in plain text "
        "first, and only call this after they explicitly confirm in their next "
        "message. Never infer or guess a recipient's email address."
    ),
    parameters={
        "doctype": {"type": "string", "required": True},
        "name": {"type": "string", "required": True},
        "recipient": {"type": "string", "required": True, "description": "Must be given explicitly by the user."},
        "subject": {"type": "string", "description": "Defaults to '<doctype>: <name>'."},
        "message": {"type": "string", "description": "Email body text."},
    },
    providers=["claude"],
)
def send_document_email(doctype, name, recipient, subject=None, message=None, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "read", doc=name)
    check_permission(doctype, "email", doc=name)

    if not recipient or "@" not in recipient:
        frappe.throw("A valid `recipient` email address is required.")

    pdf = frappe.get_print(doctype, name, as_pdf=True)

    frappe.sendmail(
        recipients=[recipient],
        subject=subject or f"{doctype}: {name}",
        message=message or f"Please find attached {doctype} {name}.",
        attachments=[{"fname": f"{name}.pdf", "fcontent": pdf}],
        reference_doctype=doctype,
        reference_name=name,
    )
    return {"status": "success", "doctype": doctype, "name": name, "sent_to": recipient}


@ai_tool(
    name="generate_print_pdf",
    description=(
        "Generate a PDF of a document using its default (or a named) print format, "
        "and attach it to the document. Returns a download link."
    ),
    parameters={
        "doctype": {"type": "string", "required": True},
        "name": {"type": "string", "required": True},
        "print_format": {"type": "string", "description": "Optional. Defaults to the DocType's default print format."},
    },
    providers=["claude"],
)
def generate_print_pdf(doctype, name, print_format=None, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "print", doc=name)

    pdf_bytes = frappe.get_print(doctype, name, print_format=print_format, as_pdf=True)

    from frappe.utils.file_manager import save_file

    file_doc = save_file(f"{name}.pdf", pdf_bytes, doctype, name, is_private=1)
    return {"status": "success", "doctype": doctype, "name": name, "file_url": file_doc.file_url}