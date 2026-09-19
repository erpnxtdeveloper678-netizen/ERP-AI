import json
import frappe
import anthropic
from erp_ai.ai.registry import get_functions
from erp_ai.ai.executor import execute_tool

DEFAULT_MODEL = "claude-sonnet-5"


# NOTE: every tool name mentioned below is registered in erp_ai/ai/tools/.
# The previous version of this prompt referenced get_doctype_schema,
# create_erp_document, execute_doc_method, and get_system_analytics - none
# of which existed anywhere in the codebase, so the model would either
# hallucinate a call that failed with "Tool not registered" or quietly
# give up on anything involving record creation.
SYSTEM_PROMPT = """
You are an AI assistant embedded in ERPNext, with tool access to query, analyze, and manage
records on behalf of the current logged-in user. You operate strictly within that user's
ERPNext permissions - every tool enforces them, so if a tool returns a permission error,
tell the user plainly that they lack the required rights; do not try to work around it.

Core Operational Rules:

1. Schema discovery:
   - Before create_document or update_document, if you're not certain of the exact field
     names or which fields are required, call get_doctype_meta first.

2. Reading & searching data:
   - Use list_documents for filtered lists, get_document for a single record by name.

3. Creating & changing records:
   - Use create_document to make a new record (e.g. Sales Order, Customer, Item, Lead, Task).
   - Use update_document to edit an existing draft record.
   - Use submit_document / cancel_document / delete_document for lifecycle actions.
     A submitted document must be cancelled before it can be updated or deleted.

4. Analytics & statistics:
   - Use analyze_data for counts, sums, averages, min/max, group-by totals (e.g. "total
     sales per customer"), and distinct values. Prefer this over fetching raw records and
     computing totals yourself - it is faster and always permission-filtered.

5. Reports, dashboards, charts & cards:
   - Use create_report to save a Report Builder view of a DocType. This is a filtered list
     view, not a computed/aggregated report - if the user wants a saved report with
     computed columns per group (e.g. "average order value per customer"), that needs a
     Query Report or Script Report with real SQL/script, which is not offered through chat
     for safety (it would execute arbitrary code every time anyone opens it). In that case,
     answer with analyze_data instead and tell the user a System Manager can turn it into a
     saved Query Report by hand if needed.
   - Use create_number_card for a single-number KPI (e.g. "Total Sales Today", "Open
     Purchase Orders", "Average Order Value") - one DocType, one aggregate (Count / Sum /
     Average / Minimum / Maximum), optionally filtered. This is what a "dashboard" request
     usually means when the user describes a metric rather than a trend or a breakdown.
   - Use create_dashboard_chart to build ONE chart: 'time_series' mode for a trend over a
     date field (e.g. monthly revenue), 'group_by' mode for totals broken down by a field
     (e.g. sales by customer). A chart is always one DocType + one aggregate - it cannot
     compute a cross-doctype figure like "Gross Profit" (Sales minus Cost of Goods Sold).
   - Neither a card nor a chart can compute a cross-doctype figure. For a request with
     several KPIs/breakdowns, call create_number_card once per plain metric and
     create_dashboard_chart once per trend/breakdown, tell the user which requested items
     you could not create natively and why, then call create_dashboard once at the end with
     every card_name and chart_name to bundle them together into one Dashboard record.
   - These all persist real records in ERPNext, so confirm the details with the user
     (title, DocType, fields, and which requested cards/charts will/won't be created as
     described) before calling them if there's any ambiguity - simply ask in plain text and
     wait for their reply in the next message; don't fabricate a confirmation.

6. Data location:
   - Line-item/child data (items on an invoice or order, etc.) lives on its own DocType,
     e.g. 'Sales Invoice Item', 'Purchase Order Item' - query or aggregate those directly
     rather than trying to pull item detail out of the parent doctype.

7. Time-bucketed totals:
   - For "per month/quarter/year" questions, use analyze_data's 'group' operation with
     `period` set to month/quarter/year (and group_by set to the relevant date field) rather
     than grouping by the raw date, which would return one row per day instead.

8. Language:
   - Match the user's language (Arabic or English). Keep responses clear and professional.
"""


def _get_anthropic_client():
    settings = frappe.get_single("AI Settings")
    api_key = settings.get_password("api_key")
    if not api_key:
        frappe.throw("Anthropic API Key is missing. Please set it in AI Settings.")

    model_name = settings.model if settings.model and "claude" in settings.model else DEFAULT_MODEL
    return anthropic.Anthropic(api_key=api_key), model_name


def _convert_param_schema(prop_data):
    prop_type = str(prop_data.get("type", "string")).lower()

    if prop_type in ("string", "text"):
        p_type = "string"
    elif prop_type in ("integer", "number", "float"):
        p_type = "integer" if prop_type == "integer" else "number"
    elif prop_type == "boolean":
        p_type = "boolean"
    elif prop_type == "object":
        p_type = "object"
    elif prop_type == "array":
        p_type = "array"
    else:
        p_type = "string"

    schema = {"type": p_type, "description": prop_data.get("description", "")}

    if "enum" in prop_data:
        schema["enum"] = prop_data["enum"]

    if p_type == "array":
        items_data = prop_data.get("items")
        schema["items"] = _convert_param_schema(items_data) if isinstance(items_data, dict) else {"type": "string"}
    elif p_type == "object" and "properties" in prop_data:
        schema["properties"] = {
            sub_name: _convert_param_schema(sub_data)
            for sub_name, sub_data in prop_data["properties"].items()
        }
        if "required" in prop_data:
            schema["required"] = prop_data["required"]

    return schema


def _build_claude_tools():
    claude_tools = []
    for fn in get_functions():
        tool_def = {
            "name": fn["name"],
            "description": fn["description"],
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": fn["parameters"].get("required") or [],
            },
        }
        for prop_name, prop_data in fn["parameters"].get("properties", {}).items():
            tool_def["input_schema"]["properties"][prop_name] = _convert_param_schema(prop_data)
        claude_tools.append(tool_def)

    return claude_tools


def _call_claude(client, model_name, messages_payload, claude_tools):
    """Anthropic SDK errors (bad request, rate limit, overloaded, etc.) were
    previously uncaught here, so they fell all the way through to api.py's
    generic handler with no clue which of the many tool calls in a
    multi-chart request actually failed. Surface a specific message instead."""
    try:
        return client.messages.create(
            model=model_name, max_tokens=2500, system=SYSTEM_PROMPT,
            messages=messages_payload, tools=claude_tools,
        )
    except anthropic.APIError as e:
        frappe.throw(f"Anthropic API error: {getattr(e, 'message', str(e))}")


def ask_claude(message: str, conversation: list = None):
    client, model_name = _get_anthropic_client()
    claude_tools = _build_claude_tools()

    messages_payload = []
    if conversation and isinstance(conversation, list):
        for msg in conversation:
            role = msg.get("role")
            content = msg.get("content")
            if role in ("user", "assistant") and content:
                messages_payload.append({"role": role, "content": content})

    messages_payload.append({"role": "user", "content": message})

    response = _call_claude(client, model_name, messages_payload, claude_tools)

    tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
    # A multi-chart dashboard (one create_dashboard_chart call per KPI, plus one
    # create_dashboard call at the end) can legitimately need a dozen+ tool calls,
    # and Claude may issue several tool_use blocks in a single turn (parallel
    # tool calls) - every one of them MUST get a matching tool_result in the
    # very next message, or the next API call fails with a 400 error like:
    # "tool_use ids were found without tool_result blocks immediately after".
    max_tool_iterations = 20
    iteration = 0

    while tool_use_blocks and iteration < max_tool_iterations:
        iteration += 1

        messages_payload.append({"role": "assistant", "content": response.content})

        tool_result_blocks = []
        for tool_use_block in tool_use_blocks:
            tool_result = execute_tool(tool_use_block.name, tool_use_block.input or {})

            tool_result_blocks.append({
                "type": "tool_result",
                "tool_use_id": tool_use_block.id,
                "content": json.dumps(tool_result, ensure_ascii=False, default=str),
            })

        # ALL tool_result blocks for this turn go in ONE user message, in the
        # same order as the tool_use blocks they answer.
        messages_payload.append({"role": "user", "content": tool_result_blocks})

        response = _call_claude(client, model_name, messages_payload, claude_tools)
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

    text_block = next((b for b in response.content if b.type == "text"), None)
    if text_block:
        return text_block.text
    if iteration >= max_tool_iterations:
        return (
            "This request needed more steps than I could complete in one go - it may be "
            "too broad (e.g. many KPIs/charts at once). Try breaking it into smaller "
            "requests, or ask me to continue."
        )
    return "Done."
    