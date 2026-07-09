import frappe
import json
from erp_ai.ai.decorators import ai_tool

@ai_tool(
    name="execute_sql",
    description="Execute custom SQL queries on the ERPNext database to calculate totals, counts, sums, profits, or custom analysis.",
    parameters={
        "query": {
            "type": "string",
            "description": "The raw SQL query to execute.",
            "required": True,
        }
    },
)
def execute_sql(query, **kwargs):
    try:
        return frappe.db.sql(query, as_dict=True)
    except Exception as e:
        return f"SQL Error during execution: {str(e)}"


@ai_tool(
    name="list_documents",
    description="List documents from any ERPNext DocType.",
    parameters={
        "doctype": {
            "type": "string",
            "description": "ERPNext DocType name.",
            "required": True,
        },
        "filters": {
            "type": "object",
            "description": "Filters for frappe.get_all().",
        },
        "fields": {
            "type": "array",
            "description": "Fields to return.",
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of documents.",
        },
    },
)
def list_documents(doctype, filters=None, fields=None, limit=20, **kwargs):
    # الحماية الذهبية: تطهير وتحويل الـ arguments لـ Python Native لمنع خطأ الـ Marshal تماماً
    clean_filters = {}
    clean_fields = ["name"]
    
    try:
        if filters:
            clean_filters = json.loads(json.dumps(filters))
        else:
            clean_filters = {}
    except Exception:
        clean_filters = filters or {}

    try:
        if fields:
            clean_fields = json.loads(json.dumps(fields))
        else:
            clean_fields = ["name"]
    except Exception:
        clean_fields = fields or ["name"]

    final_limit = limit or kwargs.get("limit", 20)

    return frappe.get_all(
        doctype,
        filters=clean_filters,
        fields=clean_fields,
        limit_page_length=final_limit,
    )


@ai_tool(
    name="get_document",
    description="Get a single ERPNext document.",
    parameters={
        "doctype": {
            "type": "string",
            "description": "ERPNext DocType name.",
            "required": True,
        },
        "name": {
            "type": "string",
            "description": "Document name.",
            "required": True,
        },
    },
)
def get_document(doctype, name, **kwargs):
    doc = frappe.get_doc(doctype, name)
    return doc.as_dict()


@ai_tool(
    name="get_doctype_meta",
    description="Return metadata for an ERPNext DocType.",
    parameters={
        "doctype": {
            "type": "string",
            "description": "ERPNext DocType name.",
            "required": True,
        }
    },
)
def get_doctype_meta(doctype, **kwargs):
    meta = frappe.get_meta(doctype)
    fields = []

    for df in meta.fields:
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