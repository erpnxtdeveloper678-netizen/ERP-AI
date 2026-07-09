from erp_ai.ai.decorators import ai_tool

import frappe


@ai_tool(
    name="ping",
    description="Check ERP connectivity."
)
def ping():

    return {
        "success": True,
        "message": "ERP is online."
    }


@ai_tool(
    name="current_user",
    description="Return current logged in user."
)
def current_user():

    return {
        "user": frappe.session.user
    }


@ai_tool(
    name="echo",
    description="Echo the text provided by the user.",
    parameters={
        "text": {
            "type": "string",
            "description": "Text to repeat back.",
            "required": True
        }
    }
)
def echo(text):

    return {
        "text": text
    }