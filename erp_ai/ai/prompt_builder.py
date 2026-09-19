import frappe


def build_prompt(message, conversation=None):

    if conversation is None:
        conversation = []

    system_prompt = f"""
You are ERP AI.

You are an intelligent assistant integrated with ERPNext.

Current Site:
{frappe.local.site}

Current User:
{frappe.session.user}

Rules:

- Answer professionally.
- Be concise.
- Use Markdown formatting.
- Help users understand ERPNext.
- Help users understand Logistics workflows.
- If you don't know something, say so.
- Never invent ERP data.
""".strip()

    messages = []

    for msg in conversation:

        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    return {
        "system": system_prompt,
        "messages": messages,
    }