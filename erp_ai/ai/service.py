import erp_ai.ai.tools
import frappe

def ask_ai(message: str, conversation=None, page_context=None):
    settings = frappe.get_single("AI Settings")

    if not settings.enabled:
        frappe.throw("AI Assistant is disabled.")

    provider = settings.provider

    if provider == "Gemini":
        from erp_ai.ai.providers.gemini import ask_gemini
        # استدعاء الدالة كـ string كامل في النظام القديم
        return ask_gemini(message, conversation, page_context=page_context)

    if provider == "Claude":
        from erp_ai.ai.providers.claude import ask_claude
        return ask_claude(message, conversation, page_context=page_context)

    frappe.throw(f"Unsupported AI Provider: {provider}")
    