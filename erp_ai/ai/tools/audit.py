"""
Audit / change-history tools, built on Frappe core's own Version doctype
(the same data the "View Version" / activity timeline in the desk UI uses).

Every tool here is registered with providers=["claude"] (see decorators.py /
registry.py) - none of them are exposed to the Gemini provider.

Follows the exact same security model as tools/documents.py: the AI model is
an untrusted caller acting as frappe.session.user, every doctype/fieldname is
validated with the shared helpers in tools/_security.py, and every action
goes through frappe's normal has_permission() checks - nothing here uses
ignore_permissions or raw SQL. Note: the Version doctype itself is commonly
restricted (e.g. to System Manager) in a given site's role permissions -
check_permission("Version", "read") will raise a clear PermissionError for
users who can't read it, same as clicking the same feature in the desk UI
would show nothing.
"""

import json

import frappe
from erp_ai.ai.decorators import ai_tool
from erp_ai.ai.tools._security import validate_doctype, check_permission


def _summarize_version(version_row):
    try:
        data = json.loads(version_row.data or "{}")
    except Exception:
        data = {}

    changed = []
    for field, old_value, new_value in (data.get("changed") or [])[:20]:
        changed.append({"field": field, "old_value": old_value, "new_value": new_value})

    return {
        "creation": version_row.creation,
        "changed_by": version_row.owner,
        "changes": changed,
    }


@ai_tool(
    name="get_document_history",
    description=(
        "Get the change history (who changed what field, and when) for one "
        "specific document, from Frappe's Version log. Use this to answer "
        "'who changed X on this record' style questions."
    ),
    parameters={
        "doctype": {"type": "string", "required": True},
        "name": {"type": "string", "required": True},
        "limit": {"type": "integer", "description": "Capped at 50. Default 20."},
    },
    providers=["claude"],
)
def get_document_history(doctype, name, limit=20, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "read", doc=name)
    validate_doctype("Version")
    check_permission("Version", "read")

    limit = max(1, min(int(limit or 20), 50))

    rows = frappe.get_list(
        "Version",
        filters={"ref_doctype": doctype, "docname": name},
        fields=["name", "owner", "creation", "data"],
        order_by="creation desc",
        limit_page_length=limit,
    )
    return {
        "doctype": doctype, "name": name, "count": len(rows),
        "history": [_summarize_version(r) for r in rows],
    }


@ai_tool(
    name="get_recent_activity",
    description=(
        "Recent edit activity across an entire DocType (not just one "
        "record) - the last N changes logged in the Version log for that "
        "DocType, each permission-checked against the specific document it "
        "touched before being returned."
    ),
    parameters={
        "doctype": {"type": "string", "required": True},
        "limit": {"type": "integer", "description": "Capped at 50. Default 20."},
    },
    providers=["claude"],
)
def get_recent_activity(doctype, limit=20, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "read")
    validate_doctype("Version")
    check_permission("Version", "read")

    limit = max(1, min(int(limit or 20), 50))

    rows = frappe.get_list(
        "Version",
        filters={"ref_doctype": doctype},
        fields=["name", "docname", "owner", "creation", "data"],
        order_by="creation desc",
        limit_page_length=limit * 2,  # over-fetch; some rows get dropped by the per-doc permission check below
    )

    activity = []
    for r in rows:
        if not frappe.has_permission(doctype, "read", doc=r.docname):
            continue
        entry = _summarize_version(r)
        entry["docname"] = r.docname
        activity.append(entry)
        if len(activity) >= limit:
            break

    return {"doctype": doctype, "count": len(activity), "activity": activity}
    