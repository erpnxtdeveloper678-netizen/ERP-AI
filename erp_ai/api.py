import json
import frappe

@frappe.whitelist()
def ask(message, conversation=None):
    if conversation:
        try:
            conversation = json.loads(conversation)
        except Exception:
            conversation = []
    else:
        conversation = []

    from erp_ai.ai.service import ask_ai
    reply = ask_ai(message=message, conversation=conversation)
    
    return {"reply": reply}