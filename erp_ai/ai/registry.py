"""
Pure tool registry. Tool *implementations* live in erp_ai/ai/tools/*.py and
register themselves via the @ai_tool decorator (erp_ai.ai.decorators).

Previously this file also defined several tools directly (run_erp_query,
manage_erp_document, create_erp_report, create_erp_dashboard) as a second,
parallel set alongside the ones in tools/*.py, using frappe.get_all() /
raw f-string SQL with no field validation. That duplication has been
removed - every tool now lives in exactly one place, in tools/, using the
shared validation helpers in tools/_security.py.
"""

TOOLS = {}


def register_tool(name, description, parameters, func):
    TOOLS[name] = {
        "name": name,
        "description": description,
        "parameters": parameters or {},
        "function": func,
    }


def get_tools():
    return TOOLS


def list_tools():
    return list(TOOLS.values())


def get_tool(name):
    return TOOLS.get(name)


def get_functions():
    """Provider-agnostic tool schema (used by the Gemini provider)."""
    functions_list = []
    for tool in TOOLS.values():
        param_properties = {}
        required_fields = []

        for param_name, param_meta in (tool.get("parameters") or {}).items():
            param_properties[param_name] = {
                "type": param_meta.get("type", "string").upper(),
                "description": param_meta.get("description", ""),
            }
            if param_meta.get("type") == "array":
                param_properties[param_name]["items"] = {"type": "STRING"}
            if param_meta.get("required"):
                required_fields.append(param_name)

        functions_list.append({
            "name": tool["name"],
            "description": tool["description"],
            "parameters": {
                "type": "OBJECT",
                "properties": param_properties,
                "required": required_fields or None,
            },
        })
    return functions_list
