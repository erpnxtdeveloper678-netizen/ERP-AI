"""
Communication tools - Frappe's "Communication" doctype (the same store
behind a document's Email/Activity timeline: sent emails, logged phone
calls, etc). This is distinct from workflow.py's add_comment (a plain
internal Comment) and send_document_email (which actually sends an email):
this tool logs an interaction that already happened (e.g. a phone call
summary) against a document's history, and reads that history back.

Every tool here is registered with providers=["claude"]. Same security
model as the rest of tools/.
"""

import frappe
from erp_ai.ai.decorators import ai_tool
from erp_ai.ai.tools._security import validate_doctype, check_permission


@ai_tool(
    name="log_communication",
    description=(
        "Log an interaction that already happened (e.g. a phone call summary, "
        "a WhatsApp/chat exchange, a meeting note) against a document's "
        "timeline, so it shows up in its Activity/Communication history. This "
        "records something that already occurred - it does NOT send anything. "
        "For actually sending an email, use send_document_email instead."
    ),
    parameters={
        "reference_doctype": {"type": "string", "required": True},
        "reference_name": {"type": "string", "required": True},
        "content": {"type": "string", "required": True, "description": "Summary/notes of the interaction."},
        "medium": {"type": "string", "description": "e.g. 'Phone', 'Chat', 'Meeting'. Defaults to 'Phone'."},
        "subject": {"type": "string", "description": "Optional short subject line."},
    },
    providers=["claude"],
)
def log_communication(reference_doctype, reference_name, content, medium=None, subject=None, **kwargs):
    validate_doctype(reference_doctype)
    check_permission(reference_doctype, "write", doc=reference_name)
    validate_doctype("Communication")
    check_permission("Communication", "create")

    if not frappe.db.exists(reference_doctype, reference_name):
        frappe.throw(f"Unknown {reference_doctype}: '{reference_name}'.")

    doc = frappe.new_doc("Communication")
    doc.reference_doctype = reference_doctype
    doc.reference_name = reference_name
    doc.communication_type = "Communication"
    doc.communication_medium = medium or "Phone"
    doc.subject = subject or f"{medium or 'Phone'} interaction logged via ERP Assistant"
    doc.content = content
    doc.sent_or_received = "Sent"
    doc.status = "Linked"
    doc.insert(ignore_permissions=True)  # Communication's own permission model is tied to the parent doc, already checked above

    return {"status": "success", "doctype": "Communication", "name": doc.name, "against": f"{reference_doctype} {reference_name}"}


@ai_tool(
    name="get_communication_history",
    description=(
        "Get the logged interaction history (calls, emails, meetings) for a "
        "document - complements get_document_history (tools/audit.py), which "
        "is about field-value changes, not conversations/interactions. If the "
        "user asks to 'summarize the conversation/communications on this "
        "record', call this first and then write the summary yourself from "
        "the returned entries - there is no separate summarization tool."
    ),
    parameters={
        "reference_doctype": {"type": "string", "required": True},
        "reference_name": {"type": "string", "required": True},
        "limit": {"type": "integer", "description": "Max rows, capped at 50. Default 20."},
    },
    providers=["claude"],
)
def get_communication_history(reference_doctype, reference_name, limit=20, **kwargs):
    validate_doctype(reference_doctype)
    check_permission(reference_doctype, "read", doc=reference_name)
    validate_doctype("Communication")
    check_permission("Communication", "read")

    if not frappe.db.exists(reference_doctype, reference_name):
        frappe.throw(f"Unknown {reference_doctype}: '{reference_name}'.")

    limit = max(1, min(int(limit or 20), 50))

    rows = frappe.get_list(
        "Communication",
        filters={"reference_doctype": reference_doctype, "reference_name": reference_name},
        fields=["name", "communication_medium", "communication_type", "subject", "content", "sender", "creation"],
        order_by="creation desc",
        limit_page_length=limit,
    )
    return {"against": f"{reference_doctype} {reference_name}", "history": rows}


@ai_tool(
    name="send_whatsapp_message",
    description=(
        "Send a WhatsApp message to a phone number, optionally linked to a "
        "document. Requires the Frappe WhatsApp app to already be installed "
        "and configured on this site (its own WhatsApp Business API "
        "credentials) - this tool only creates the message record that "
        "app's own integration sends; it never talks to WhatsApp directly "
        "itself. If that app isn't installed, this fails with a clear "
        "'Unknown DocType' error rather than doing nothing silently. "
        "ALWAYS show the user the exact phone number and message text and "
        "wait for their explicit confirmation before calling this - same "
        "rule as send_document_email."
    ),
    parameters={
        "to": {"type": "string", "required": True, "description": "Recipient phone number, with country code."},
        "message": {"type": "string", "required": True},
        "reference_doctype": {"type": "string", "description": "Optional. Links the message to a document."},
        "reference_name": {"type": "string", "description": "Optional. Required if reference_doctype is given."},
    },
    providers=["claude"],
)
def send_whatsapp_message(to, message, reference_doctype=None, reference_name=None, **kwargs):
    validate_doctype("WhatsApp Message")
    check_permission("WhatsApp Message", "create")

    if reference_doctype:
        validate_doctype(reference_doctype)
        if reference_name and not frappe.db.exists(reference_doctype, reference_name):
            frappe.throw(f"Unknown {reference_doctype}: '{reference_name}'.")

    doc = frappe.new_doc("WhatsApp Message")
    doc.to = to
    doc.message = message
    if hasattr(doc, "content_type"):
        doc.content_type = "text"
    if reference_doctype:
        doc.reference_doctype = reference_doctype
        doc.reference_name = reference_name
    doc.insert()

    return {"status": "success", "doctype": "WhatsApp Message", "name": doc.name, "to": to}
    