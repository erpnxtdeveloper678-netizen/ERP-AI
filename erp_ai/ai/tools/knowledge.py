"""
Knowledge Base tools - searches whichever documentation doctype this site
actually has installed (Frappe Helpdesk's "HD Article", or Frappe's core
"Help Article"). Tries them in order and gives a clear error naming what's
missing if neither is installed, rather than failing obscurely.

Every tool here is registered with providers=["claude"]. Same security
model as the rest of tools/.
"""

import frappe
from erp_ai.ai.decorators import ai_tool
from erp_ai.ai.tools._security import validate_doctype, check_permission

# Tried in order. (doctype, title_field, content_field, published_filter)
_KB_CANDIDATES = [
    ("HD Article", "title", "content", {"status": "Published"}),
    ("Help Article", "title", "content", {"published": 1}),
]


def _find_kb_doctype():
    for doctype, title_field, content_field, published_filter in _KB_CANDIDATES:
        if frappe.db.exists("DocType", doctype):
            return doctype, title_field, content_field, published_filter
    return None


@ai_tool(
    name="search_knowledge_base",
    description=(
        "Search this site's internal knowledge base / help articles for a topic. "
        "Use this before telling a user 'I don't know how that works here' - "
        "the answer may be documented internally even if it's not standard ERPNext."
    ),
    parameters={
        "query": {"type": "string", "required": True},
        "limit": {"type": "integer", "description": "Max results, capped at 20. Default 10."},
    },
    providers=["claude"],
)
def search_knowledge_base(query, limit=10, **kwargs):
    found = _find_kb_doctype()
    if not found:
        frappe.throw(
            "No knowledge base app is installed on this site (checked for "
            "'HD Article' and 'Help Article'). There is no internal documentation to search."
        )
    doctype, title_field, content_field, published_filter = found
    validate_doctype(doctype)
    check_permission(doctype, "read")

    limit = max(1, min(int(limit or 10), 20))

    filters = dict(published_filter)
    or_filters = [[title_field, "like", f"%{query}%"], [content_field, "like", f"%{query}%"]]

    rows = frappe.get_list(
        doctype,
        filters=filters,
        or_filters=or_filters,
        fields=["name", title_field, content_field],
        limit_page_length=limit,
    )

    results = []
    for r in rows:
        content = (r.get(content_field) or "")
        snippet = content[:280] + ("..." if len(content) > 280 else "")
        results.append({"name": r["name"], "title": r.get(title_field), "snippet": snippet})

    return {"source_doctype": doctype, "query": query, "results": results}


@ai_tool(
    name="get_knowledge_base_article",
    description="Get the full content of one knowledge base article by its ID (from search_knowledge_base).",
    parameters={"article": {"type": "string", "required": True}},
    providers=["claude"],
)
def get_knowledge_base_article(article, **kwargs):
    found = _find_kb_doctype()
    if not found:
        frappe.throw("No knowledge base app is installed on this site.")
    doctype, title_field, content_field, _ = found
    validate_doctype(doctype)
    check_permission(doctype, "read", doc=article)

    if not frappe.db.exists(doctype, article):
        frappe.throw(f"Unknown {doctype}: '{article}'.")

    doc = frappe.get_doc(doctype, article)
    return {
        "name": doc.name,
        "title": getattr(doc, title_field, None),
        "content": getattr(doc, content_field, None),
    }


@ai_tool(
    name="search_resolved_tickets",
    description=(
        "Search past CLOSED/RESOLVED support tickets for a similar problem - "
        "'has this come up before, and how was it solved?'. Complements "
        "search_knowledge_base: this searches real past cases and their "
        "resolutions rather than written documentation. Requires the "
        "Helpdesk app (HD Ticket) to be installed."
    ),
    parameters={
        "query": {"type": "string", "required": True},
        "limit": {"type": "integer", "description": "Max results, capped at 20. Default 10."},
    },
    providers=["claude"],
)
def search_resolved_tickets(query, limit=10, **kwargs):
    validate_doctype("HD Ticket")
    check_permission("HD Ticket", "read")

    limit = max(1, min(int(limit or 10), 20))
    meta = frappe.get_meta("HD Ticket")
    detail_field = "resolution_details" if meta.get_field("resolution_details") else "description"

    rows = frappe.get_list(
        "HD Ticket",
        filters={"status": ["in", ["Resolved", "Closed"]]},
        or_filters=[["subject", "like", f"%{query}%"], ["description", "like", f"%{query}%"]],
        fields=["name", "subject", detail_field],
        order_by="modified desc",
        limit_page_length=limit,
    )
    return {"query": query, "past_cases": rows}
    