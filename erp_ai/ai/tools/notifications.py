"""
Notification Center tools - Frappe's built-in "Notification Log" doctype
(the same store behind the bell icon in the desk UI). No email/SMS sending
here - see workflow.py's send_document_email for that; this is purely
in-app notifications.

Every tool here is registered with providers=["claude"]. Same security
model as the rest of tools/.
"""

import frappe
from erp_ai.ai.decorators import ai_tool
from erp_ai.ai.tools._security import validate_doctype, check_permission


@ai_tool(
    name="send_notification",
    description=(
        "Send an in-app notification (bell-icon alert) to one or more ERPNext "
        "users - NOT an email. Optionally link it to a document so clicking it "
        "opens that record. Always confirm the recipient(s) and message with "
        "the user before sending."
    ),
    parameters={
        "to_users": {"type": "array", "required": True, "description": "List of user emails to notify."},
        "subject": {"type": "string", "required": True},
        "message": {"type": "string", "description": "Optional longer body. Defaults to the subject."},
        "reference_doctype": {"type": "string", "description": "Optional. Links the notification to a document."},
        "reference_name": {"type": "string", "description": "Optional. Required if reference_doctype is given."},
    },
    providers=["claude"],
)
def send_notification(to_users, subject, message=None, reference_doctype=None, reference_name=None, **kwargs):
    validate_doctype("Notification Log")

    if isinstance(to_users, str):
        to_users = [u.strip() for u in to_users.split(",") if u.strip()]
    if not isinstance(to_users, list) or not to_users:
        frappe.throw("`to_users` must be a non-empty list of user emails.")

    if reference_doctype:
        validate_doctype(reference_doctype)
        if reference_name and not frappe.db.exists(reference_doctype, reference_name):
            frappe.throw(f"Unknown {reference_doctype}: '{reference_name}'.")

    sent_to = []
    for user in to_users:
        if not frappe.db.exists("User", user):
            continue  # skip unknown recipients rather than failing the whole batch
        doc = frappe.new_doc("Notification Log")
        doc.for_user = user
        doc.from_user = frappe.session.user
        doc.type = "Alert"
        doc.subject = subject
        if message:
            doc.email_content = message
        if reference_doctype:
            doc.document_type = reference_doctype
            doc.document_name = reference_name
        doc.insert(ignore_permissions=True)  # a notification is only ever visible to for_user; not a data-access grant
        sent_to.append(user)

    skipped = [u for u in to_users if u not in sent_to]
    return {"status": "success", "sent_to": sent_to, "skipped_unknown_users": skipped}


@ai_tool(
    name="get_my_notifications",
    description="List the current user's in-app notifications (bell icon).",
    parameters={
        "unread_only": {"type": "boolean", "description": "Default true."},
        "limit": {"type": "integer", "description": "Max rows, capped at 50. Default 20."},
    },
    providers=["claude"],
)
def get_my_notifications(unread_only=True, limit=20, **kwargs):
    validate_doctype("Notification Log")
    check_permission("Notification Log", "read")

    limit = max(1, min(int(limit or 20), 50))
    filters = {"for_user": frappe.session.user}
    if unread_only:
        filters["read"] = 0

    rows = frappe.get_list(
        "Notification Log",
        filters=filters,
        fields=["name", "subject", "type", "document_type", "document_name", "creation", "read"],
        order_by="creation desc",
        limit_page_length=limit,
    )
    return {"user": frappe.session.user, "notifications": rows}
    