import json
import frappe
import anthropic
from erp_ai.ai.registry import get_tools, get_functions

DEFAULT_MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """
You are the master AI Engine for ERPNext with full autonomous tool-use capabilities.
Your primary role is to act as an intelligent co-pilot inside ERPNext, enabling users to manage, query, analyze, and automate their ERP operations smoothly.

Core Operational Rules:
1. **Schema & Field Discovery**:
   - If a user asks to create or update a record and you are unsure of the field names or mandatory fields, run `get_doctype_schema` FIRST to inspect the DocType metadata.

2. **Creating & Updating Records**:
   - Use `create_erp_document` to build and save any new ERPNext record (e.g., Sales Order, Customer, Item, Lead, Task, Journal Entry, etc.).
   - Ensure the JSON data passed to `create_erp_document` accurately reflects field names derived from the schema or standard ERPNext fields.

3. **Data Fetching & Child Tables**:
   - Use `run_erp_query` to query records.
   - When detailed transactional line items are required (e.g., items inside an invoice or order), populate `include_child_table` (e.g., 'Sales Invoice Item').

4. **Analytics & Metrics**:
   - For high-level calculations (e.g., total sales per customer, count of open tasks, average invoice value), use `get_system_analytics` to perform direct SQL-level aggregations (COUNT, SUM, AVG) instead of manually looping over lists.

5. **Document Actions & Methods**:
   - Use `manage_erp_document` for primary lifecycle actions: 'submit', 'cancel', 'update', or 'delete'.
   - Use `execute_doc_method` to invoke specific python methods attached to document instances.

6. **Dashboards & Reports**:
   - Use `create_erp_dashboard` to set up visual analytics with Number Cards and Time-series Charts.
   - CRITICAL DASHBOARD RULE: In Frappe Dashboard Charts, `type` MUST be an aggregate function ('Count', 'Sum', 'Average', 'Group By', etc.). `chart_type` is the visual representation ('Line', 'Bar', 'Pie', 'Donut'). NEVER pass 'Line' or 'Bar' to the `type` field!
   - Use `create_erp_report` when creating saved Builder or Query Reports.

7. **Permissions & Security**:
   - Always operate within system boundaries. If a tool returns a permission error, inform the user politely that they lack the required rights for that action.

8. **Language Policy**:
   - Match the user's language natively (Arabic or English). Keep your response clear, well-structured, precise, and professional.
"""


def _get_anthropic_client():
    """
    جلب الإعدادات وإنشاء العميل الخاص بـ Anthropic API
    """
    settings = frappe.get_single("AI Settings")
    api_key = settings.get_password("api_key")
    if not api_key:
        raise frappe.ValidationError("Anthropic API Key is missing. Please set it in AI Settings.")
    
    model_name = settings.model if settings.model and "claude" in settings.model else DEFAULT_MODEL
    client = anthropic.Anthropic(api_key=api_key)
    return client, model_name


def _convert_param_schema(prop_data):
    """
    دالة مساعدة لتحويل خصائص البارامترات إلى تنسيق JSON Schema الصحيح والمتوافق مع Anthropic (يدعم الخصائص المتداخلة والـ Enum والـ Objects)
    """
    prop_type = str(prop_data.get("type", "string")).lower()

    if prop_type in ["string", "text"]:
        p_type = "string"
    elif prop_type in ["integer", "number", "float"]:
        p_type = "number" if prop_type != "integer" else "integer"
    elif prop_type == "boolean":
        p_type = "boolean"
    elif prop_type == "object":
        p_type = "object"
    elif prop_type == "array":
        p_type = "array"
    else:
        p_type = "string"

    schema = {
        "type": p_type,
        "description": prop_data.get("description", "")
    }

    if "enum" in prop_data:
        schema["enum"] = prop_data["enum"]

    # التعامل مع القوائم (Arrays) بشكل مختلف حسب محتواها (Objects أم عناصر عادية)
    if p_type == "array":
        items_data = prop_data.get("items")
        if items_data and isinstance(items_data, dict):
            schema["items"] = _convert_param_schema(items_data)
        else:
            schema["items"] = {"type": "string"}

    # التعامل مع الكائنات (Objects) لتمرير خصائصها المتداخلة
    elif p_type == "object" and "properties" in prop_data:
        schema["properties"] = {}
        for sub_name, sub_data in prop_data["properties"].items():
            schema["properties"][sub_name] = _convert_param_schema(sub_data)
        if "required" in prop_data:
            schema["required"] = prop_data["required"]

    return schema


def _build_claude_tools():
    """
    تحويل الأدوات المسجلة في registry.py إلى التنسيق المتوافق مع Anthropic Tools Schema
    """
    raw_functions = get_functions()
    claude_tools = []

    for fn in raw_functions:
        tool_def = {
            "name": fn["name"],
            "description": fn["description"],
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": fn["parameters"].get("required") or []
            }
        }
        
        props = fn["parameters"].get("properties", {})
        for prop_name, prop_data in props.items():
            tool_def["input_schema"]["properties"][prop_name] = _convert_param_schema(prop_data)

        claude_tools.append(tool_def)

    return claude_tools


def _execute_tool_call(tool_name, tool_inputs):
    """
    تنفيذ الدالة المستهدفة من سجل الأدوات (registry.py) وتمرير المعاملات المحددة من قبل الـ AI
    """
    tools_registry = get_tools()
    tool_meta = tools_registry.get(tool_name)

    if not tool_meta or not tool_meta.get("function"):
        return {"error": f"Tool '{tool_name}' is not registered."}

    func = tool_meta["function"]
    
    try:
        result = func(**tool_inputs)
        return result
    except Exception as e:
        frappe.log_error(title=f"ERP AI Tool Execution Error [{tool_name}]", message=frappe.get_traceback())
        return {"error": str(e)}


def ask_ai(message: str, conversation: list = None):
    """
    دالة المحادثة الرئيسية مع Anthropic Claude مع دعم دورة تنفيذ الأدوات (Tool Execution Loop)
    """
    client, model_name = _get_anthropic_client()
    claude_tools = _build_claude_tools()

    messages_payload = []
    if conversation and isinstance(conversation, list):
        for msg in conversation:
            role = msg.get("role")
            content = msg.get("content")
            if role in ["user", "assistant"] and content:
                messages_payload.append({"role": role, "content": content})

    messages_payload.append({"role": "user", "content": message})

    try:
        response = client.messages.create(
            model=model_name,
            max_tokens=2500,
            system=SYSTEM_PROMPT,
            messages=messages_payload,
            tools=claude_tools
        )

        tool_use_block = next((b for b in response.content if b.type == "tool_use"), None)

        max_tool_iterations = 5
        iteration = 0

        while tool_use_block and iteration < max_tool_iterations:
            iteration += 1
            tool_name = tool_use_block.name
            tool_inputs = tool_use_block.input or {}

            tool_result = _execute_tool_call(tool_name, tool_inputs)

            messages_payload.append({"role": "assistant", "content": response.content})
            messages_payload.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_block.id,
                        "content": json.dumps(tool_result, ensure_ascii=False)
                    }
                ]
            })

            response = client.messages.create(
                model=model_name,
                max_tokens=2500,
                system=SYSTEM_PROMPT,
                messages=messages_payload,
                tools=claude_tools
            )

            tool_use_block = next((b for b in response.content if b.type == "tool_use"), None)

        text_block = next((b for b in response.content if b.type == "text"), None)
        return text_block.text if text_block else "تم تنفيذ العملية بنجاح."

    except Exception as e:
        frappe.log_error(title="ERP AI Service Error", message=frappe.get_traceback())
        raise e