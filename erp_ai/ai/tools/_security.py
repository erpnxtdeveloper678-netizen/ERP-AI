"""
Shared validation & permission helpers for every AI tool.

Design principle: the AI model is treated as an UNTRUSTED caller acting on
behalf of frappe.session.user. Nothing here ever runs a query built from a
raw, model-supplied string. Every identifier (doctype name, field name,
sort field, filter key) is checked against an allowlist derived from the
DocType's own metadata *before* it is allowed anywhere near a query, and
every data access goes through frappe.get_list()/frappe.has_permission()
so ERPNext's normal role/owner/user-permission rules are enforced exactly
as they would be in the desk UI.

If you are adding a new tool: never use frappe.db.sql() with interpolated
strings, never use frappe.get_all() (it skips permission checks), and
always validate identifiers with the helpers below.
"""

import json
import frappe

# Columns that exist on every DocType regardless of its field list.
STANDARD_FIELDS = {
    "name", "creation", "modified", "modified_by", "owner", "docstatus", "idx",
}

# Layout-only fieldtypes that can never legally appear in a query.
NON_DATA_FIELDTYPES = {"Section Break", "Column Break", "Tab Break", "HTML", "Button"}

AGGREGATE_FUNCTIONS = {"count", "sum", "avg", "min", "max"}


def validate_doctype(doctype):
    """Confirm this is a real, installed DocType. Raises frappe.ValidationError otherwise."""
    if not doctype or not isinstance(doctype, str):
        frappe.throw("A valid `doctype` is required.")
    if not frappe.db.exists("DocType", doctype):
        frappe.throw(f"Unknown DocType: '{doctype}'.")
    return doctype


def check_permission(doctype, ptype="read", doc=None):
    """Thin wrapper so every tool raises the same, clear error on the same condition."""
    if not frappe.has_permission(doctype, ptype, doc=doc):
        frappe.throw(
            f"You do not have '{ptype}' permission on {doctype}"
            + (f" {doc}" if doc else "") + ".",
            frappe.PermissionError,
        )


def get_queryable_fieldnames(doctype):
    """Allowlist of column names that may legally appear in a filter/select/order-by
    for this doctype. Anything not in this set is rejected before it reaches SQL."""
    meta = frappe.get_meta(doctype)
    valid = set(STANDARD_FIELDS)
    for df in meta.fields:
        if df.fieldtype not in NON_DATA_FIELDTYPES:
            valid.add(df.fieldname)
    return valid


def get_writable_fieldnames(doctype):
    """Allowlist of fields an AI-driven create/update may set. Excludes read-only,
    hidden, and system-managed fields even though they're 'queryable' for reads."""
    meta = frappe.get_meta(doctype)
    valid = set()
    for df in meta.fields:
        if df.fieldtype in NON_DATA_FIELDTYPES:
            continue
        if df.read_only or df.hidden:
            continue
        valid.add(df.fieldname)
    return valid


def validate_fieldname(doctype, fieldname, allow_password=False):
    if not fieldname or not isinstance(fieldname, str):
        frappe.throw("A valid field name is required.")
    fieldname = fieldname.strip().strip("`")
    if fieldname not in get_queryable_fieldnames(doctype):
        frappe.throw(f"'{fieldname}' is not a recognized field on {doctype}.")
    if not allow_password:
        meta = frappe.get_meta(doctype)
        df = meta.get_field(fieldname)
        if df and df.fieldtype == "Password":
            frappe.throw(f"Access to the password field '{fieldname}' is not permitted.")
    return fieldname


def validate_fields(doctype, fields):
    """Normalize + validate a list of field names for a select clause."""
    if not fields:
        return ["name"]
    if isinstance(fields, str):
        try:
            fields = json.loads(fields)
        except Exception:
            fields = [f.strip() for f in fields.split(",") if f.strip()]
    if not isinstance(fields, list):
        frappe.throw("`fields` must be a list of field names.")
    return [validate_fieldname(doctype, f) for f in fields]


def validate_order_by(doctype, order_by, default="creation desc"):
    """Validate a single 'field [asc|desc]' expression. Rejects anything else,
    including multi-field or raw-SQL order-by strings."""
    if not order_by:
        return default
    parts = order_by.strip().split()
    field = parts[0]
    direction = parts[1].lower() if len(parts) > 1 else "asc"
    if direction not in ("asc", "desc"):
        direction = "asc"
    validate_fieldname(doctype, field)
    return f"{field} {direction}"


def parse_filters(filters):
    if filters is None:
        return {}
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except Exception:
            frappe.throw("`filters` must be valid JSON.")
    if not isinstance(filters, dict):
        frappe.throw("`filters` must be an object of {field: value}.")
    return filters


def validate_filters(doctype, filters):
    """Validate filter keys against the doctype's real fields. Values are left as-is:
    frappe.get_list() parameterizes filter values internally, so injection risk lives
    entirely in the *identifiers* (keys), which this function locks down."""
    filters = parse_filters(filters)
    clean = {}
    for key, value in filters.items():
        validate_fieldname(doctype, key)
        clean[key] = value
    return clean


def parse_json_object(value, param_name="data"):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            frappe.throw(f"`{param_name}` must be valid JSON.")
    if not isinstance(value, dict):
        frappe.throw(f"`{param_name}` must be an object.")
    return value
