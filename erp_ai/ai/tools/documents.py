import frappe
from erp_ai.ai.decorators import ai_tool
from erp_ai.ai.tools._security import (
    validate_doctype,
    validate_fields,
    validate_filters,
    validate_order_by,
    check_permission,
    get_writable_fieldnames,
    parse_json_object,
)

# NOTE: `execute_sql` has been intentionally removed. It let the model run
# arbitrary, unrestricted SQL against the whole database with no permission
# checks whatsoever - equivalent to giving every chat user root DB access.
# Every use case it covered (counts, sums, averages, group-by totals,
# distinct values, filtered lists) is covered below through
# frappe.get_list(), which enforces the same role/owner/user-permission
# rules as the desk UI.


@ai_tool(
    name="list_documents",
    description=(
        "List documents from an ERPNext DocType. Results are automatically "
        "restricted to what the current user is allowed to see (role permissions, "
        "user permissions, and record sharing all apply, same as the desk UI). "
        "If you're not certain of the exact DocType name, call find_doctype first - "
        "a wrong-but-existing DocType returns 0 rows, not an error."
    ),
    parameters={
        "doctype": {"type": "string", "required": True, "description": "Exact ERPNext DocType name."},
        "filters": {"type": "object", "description": "e.g. {\"status\": \"Open\"}"},
        "fields": {"type": "array", "description": "Field names to return. Defaults to ['name']."},
        "order_by": {"type": "string", "description": "e.g. 'posting_date desc'. Single field only."},
        "limit": {"type": "integer", "description": "Max rows, capped at 500."},
    },
)
def list_documents(doctype, filters=None, fields=None, order_by=None, limit=20, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "read")

    clean_fields = validate_fields(doctype, fields)
    clean_filters = validate_filters(doctype, filters)
    clean_order = validate_order_by(doctype, order_by)
    limit = max(1, min(int(limit or 20), 500))

    return frappe.get_list(
        doctype,
        filters=clean_filters,
        fields=clean_fields,
        order_by=clean_order,
        limit_page_length=limit,
    )


@ai_tool(
    name="get_document",
    description="Fetch a single ERPNext document by name. Requires read permission on that record.",
    parameters={
        "doctype": {"type": "string", "required": True},
        "name": {"type": "string", "required": True, "description": "The document's ID/name."},
    },
)
def get_document(doctype, name, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "read", doc=name)

    doc = frappe.get_doc(doctype, name)
    data = doc.as_dict()

    # Defensive redaction: password-type fields should never reach the model,
    # even though Frappe normally omits them from as_dict() already.
    meta = frappe.get_meta(doctype)
    for df in meta.fields:
        if df.fieldtype == "Password":
            data.pop(df.fieldname, None)

    return data


@ai_tool(
    name="find_doctype",
    description=(
        "Search installed DocTypes by name to find the exact DocType name to use in "
        "other tools (list_documents, analyze_data, get_doctype_meta, run_report, "
        "etc). The user's wording (e.g. 'freight', 'shipments', 'invoices') is often "
        "not the literal DocType name. ALWAYS use this before calling another tool "
        "with a DocType name you are not 100% certain of - a wrong-but-existing "
        "DocType silently returns 0 rows instead of an error, which looks exactly "
        "like 'there is no data' even when the data exists under a different name. "
        "Only results the current user has at least read access to are returned."
    ),
    parameters={
        "search": {"type": "string", "required": True, "description": "Partial DocType name, e.g. 'freight'."},
        "limit": {"type": "integer", "description": "Max results, capped at 20. Default 10."},
    },
)
def find_doctype(search, limit=10, **kwargs):
    if not search or not isinstance(search, str) or not search.strip():
        frappe.throw("A search term is required.")

    limit = max(1, min(int(limit or 10), 20))

    # frappe.get_list on the "DocType" doctype itself - DocType *definitions*
    # are schema/metadata, not business records, so this is safe to search
    # broadly. We still only hand back matches the user can actually read,
    # so the AI is never pointed at a DocType it will just hit a
    # PermissionError on next.
    candidates = frappe.get_list(
        "DocType",
        filters=[["name", "like", f"%{search.strip()}%"]],
        fields=["name", "module", "istable"],
        order_by="name asc",
        limit_page_length=200,
    )

    matches = []
    for d in candidates:
        if frappe.has_permission(d["name"], "read"):
            matches.append({
                "doctype": d["name"],
                "module": d.get("module"),
                "is_child_table": bool(d.get("istable")),
            })
        if len(matches) >= limit:
            break

    return {"search": search, "matches": matches}


@ai_tool(
    name="get_doctype_meta",
    description=(
        "Return field metadata for an ERPNext DocType: field names, types, labels, "
        "required/read-only flags. Always call this before create_document or "
        "update_document if you're not certain of the exact field names. If you're "
        "not certain of the exact DocType name either, call find_doctype first."
    ),
    parameters={"doctype": {"type": "string", "required": True}},
)
def get_doctype_meta(doctype, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "read")

    meta = frappe.get_meta(doctype)
    fields = []
    for df in meta.fields:
        if df.fieldtype == "Password":
            continue
        fields.append({
            "fieldname": df.fieldname,
            "label": df.label,
            "fieldtype": df.fieldtype,
            "options": df.options,
            "reqd": df.reqd,
            "read_only": df.read_only,
            "hidden": df.hidden,
            "in_list_view": df.in_list_view,
        })

    return {
        "doctype": meta.name,
        "module": meta.module,
        "istable": meta.istable,
        "search_fields": meta.search_fields,
        "title_field": meta.title_field,
        "fields": fields,
    }


@ai_tool(
    name="create_document",
    description=(
        "Create a new ERPNext document. Only fields that are writable (not read-only, "
        "not hidden, not a system field) will be accepted; call get_doctype_meta first "
        "if you're unsure of required fields."
    ),
    parameters={
        "doctype": {"type": "string", "required": True},
        "data": {"type": "object", "required": True, "description": "Field values for the new document."},
    },
)
def create_document(doctype, data, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "create")

    data = parse_json_object(data)
    allowed = get_writable_fieldnames(doctype)
    clean_data = {k: v for k, v in data.items() if k in allowed}

    doc = frappe.new_doc(doctype)
    doc.update(clean_data)
    doc.insert()  # normal permission-checked insert - no ignore_permissions
    return {"status": "success", "doctype": doctype, "name": doc.name}


@ai_tool(
    name="update_document",
    description="Update fields on an existing, non-submitted ERPNext document.",
    parameters={
        "doctype": {"type": "string", "required": True},
        "name": {"type": "string", "required": True},
        "data": {"type": "object", "required": True, "description": "Field values to change."},
    },
)
def update_document(doctype, name, data, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "write", doc=name)

    doc = frappe.get_doc(doctype, name)
    if doc.docstatus != 0:
        frappe.throw("Cannot edit a submitted or cancelled document; cancel it first.")

    data = parse_json_object(data)
    allowed = get_writable_fieldnames(doctype)
    clean_data = {k: v for k, v in data.items() if k in allowed}

    doc.update(clean_data)
    doc.save()
    return {"status": "success", "doctype": doctype, "name": doc.name}


@ai_tool(
    name="submit_document",
    description="Submit a draft ERPNext document (docstatus 0 -> 1).",
    parameters={"doctype": {"type": "string", "required": True}, "name": {"type": "string", "required": True}},
)
def submit_document(doctype, name, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "submit", doc=name)

    doc = frappe.get_doc(doctype, name)
    if doc.docstatus != 0:
        frappe.throw(f"'{name}' is not a draft, so it cannot be submitted.")
    doc.submit()
    return {"status": "success", "doctype": doctype, "name": doc.name}


@ai_tool(
    name="cancel_document",
    description="Cancel a submitted ERPNext document (docstatus 1 -> 2).",
    parameters={"doctype": {"type": "string", "required": True}, "name": {"type": "string", "required": True}},
)
def cancel_document(doctype, name, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "cancel", doc=name)

    doc = frappe.get_doc(doctype, name)
    if doc.docstatus != 1:
        frappe.throw(f"'{name}' is not submitted, so it cannot be cancelled.")
    doc.cancel()
    return {"status": "success", "doctype": doctype, "name": doc.name}


@ai_tool(
    name="delete_document",
    description="Permanently delete a draft (never-submitted) ERPNext document.",
    parameters={"doctype": {"type": "string", "required": True}, "name": {"type": "string", "required": True}},
)
def delete_document(doctype, name, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "delete", doc=name)

    doc = frappe.get_doc(doctype, name)
    if doc.docstatus != 0:
        frappe.throw("Cannot delete a submitted or cancelled document; cancel it first.")
    frappe.delete_doc(doctype, name)
    return {"status": "success", "doctype": doctype, "name": name}