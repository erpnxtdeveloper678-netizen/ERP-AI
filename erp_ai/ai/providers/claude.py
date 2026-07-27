import json
import frappe
import anthropic
from erp_ai.ai.registry import get_functions
from erp_ai.ai.executor import execute_tool


SYSTEM_PROMPT = """
You are "ERP Assistant", a professional AI business analyst embedded inside an ERPNext/Frappe system with direct access to live company data through execution tools.

## Identity & Scope
- You assist employees with queries about sales, purchases, inventory, accounting, HR, and other ERPNext modules.
- You only answer using data returned by the tools available to you, or general ERPNext/business knowledge. You never invent figures, names, dates, or IDs.
- If a question falls outside ERP data or business operations (e.g. general trivia, coding help, personal advice), politely redirect the user back to ERP-related topics.

## Language
- Always reply in the exact language and dialect the user used in their last message (Arabic → Arabic, English → English, Egyptian/Gulf/Levantine dialect → mirror it naturally). Never mix languages in one reply unless the user did.
- This rule overrides everything else: the language of tool names, tool descriptions, ERP data, column headers, or entity names must NEVER change your reply language.

## Data Integrity Rules
1. Never fabricate or estimate numbers. If a tool returns a total_count of 0, state clearly that there are no records found (e.g. "لا توجد سجلات حالياً") instead of throwing an error.
2. Never output raw JSON, dictionaries, stack traces, or code blocks to the user. Always translate tool results into a natural, professional sentence or short paragraph.
3. When presenting monetary values, always state the currency. Format large numbers with thousand separators for readability.
4. When presenting dates, use a clear human format.
5. If the user's request is ambiguous, ask a single clarifying question before calling the tool.

## Tool Use
- Use available tools whenever the user's question requires current or specific ERP data.
- If total_count is explicitly 0, acknowledge it accurately as a valid zero result.
"""

FALLBACK_NO_KEY = {
    "English": "The API key is not configured in system settings. Please check your configuration.",
    "Arabic": "مفتاح الـ API غير مُعد في إعدادات النظام. برجاء مراجعة الإعدادات.",
}
FALLBACK_TOOL_PARSE_ERROR = {
    "English": "Sorry, something went wrong while processing the requested data.",
    "Arabic": "عذراً، حدث خطأ أثناء معالجة البيانات المطلوبة.",
}
FALLBACK_TOOL_EXEC_ERROR = {
    "English": "Sorry, no matching data could be found in the system for this request.",
    "Arabic": "عذراً، لم يتم العثور على بيانات مطابقة في النظام لهذا الطلب.",
}
FALLBACK_NO_RESULTS = {
    "English": "Sorry, there are no matching records in the system.",
    "Arabic": "عذراً، لا توجد سجلات مطابقة في النظام.",
}
FALLBACK_PRESENTATION_ERROR = {
    "English": "Sorry, the requested data was retrieved successfully, but an error occurred while formatting the reply.",
    "Arabic": "عذراً، تم استخراج البيانات المطلوبة بنجاح، لكن حدث خطأ أثناء صياغة الرد.",
}
FALLBACK_STREAM_ERROR = {
    "English": "Sorry, an error occurred while processing the reply.",
    "Arabic": "عذراً، حدث خطأ أثناء معالجة الرد.",
}
FALLBACK_CRITICAL_ERROR = {
    "English": "An unexpected error occurred while processing your request.",
    "Arabic": "حدث خطأ غير متوقع أثناء معالجة الطلب.",
}

DEFAULT_MODEL = "claude-sonnet-5"


def _detect_language_label(text: str) -> str:
    if not text:
        return "English"
    for ch in text:
        if "\u0600" <= ch <= "\u06FF":
            return "Arabic"
    return "English"


def _build_tools():
    raw_functions = get_functions()
    tools = []
    if not raw_functions:
        return tools

    for f in raw_functions:
        name = f.get("name")
        description = f.get("description", "")
        parameters = f.get("parameters") or f.get("input_schema") or {}
        if not isinstance(parameters, dict):
            parameters = {}

        properties = parameters.get("properties", {})
        if not isinstance(properties, dict):
            properties = {}

        cleaned_properties = {}
        for prop_name, prop_val in properties.items():
            if isinstance(prop_val, dict):
                p_type = prop_val.get("type", "string")
                if p_type not in ["string", "number", "integer", "boolean", "array", "object"]:
                    p_type = "string"
                cleaned_properties[prop_name] = {
                    "type": p_type,
                    "description": prop_val.get("description", "")
                }
            else:
                cleaned_properties[prop_name] = {"type": "string", "description": ""}

        input_schema = {
            "type": "object",
            "properties": cleaned_properties
        }

        if "required" in parameters and isinstance(parameters["required"], list):
            input_schema["required"] = [str(r) for r in parameters["required"]]

        tools.append({
            "name": name,
            "description": description,
            "input_schema": input_schema
        })

    return tools


def _build_messages(message, conversation):
    messages = []
    if conversation:
        try:
            conv = json.loads(conversation) if isinstance(conversation, str) else conversation
            for msg in conv:
                role = "user" if msg.get("role") == "user" else "assistant"
                messages.append({"role": role, "content": msg.get("content", "")})
        except Exception:
            pass

    messages.append({"role": "user", "content": message})
    return messages


def ask_claude(message: str, conversation=None):
    lang = _detect_language_label(message)

    try:
        settings = frappe.get_single("AI Settings")
        api_key = settings.get_password("api_key")

        if not api_key:
            yield FALLBACK_NO_KEY[lang]
            return

        client = anthropic.Anthropic(api_key=api_key)
        model_name = settings.model if settings.model and "claude" in settings.model else DEFAULT_MODEL

        messages = _build_messages(message, conversation)
        messages[-1] = {
            "role": "user",
            "content": f"{message}\n\n(Reminder to assistant: reply entirely in {lang}.)"
        }
        tools = _build_tools()

        kwargs = {
            "model": model_name,
            "max_tokens": 4096,
            "system": SYSTEM_PROMPT,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        try:
            response = client.messages.create(**kwargs)
        except Exception:
            try:
                kwargs["model"] = DEFAULT_MODEL
                response = client.messages.create(**kwargs)
            except Exception:
                frappe.log_error(frappe.get_traceback(), "ERP AI Model Call Error")
                yield FALLBACK_STREAM_ERROR[lang]
                return

        if response.stop_reason == "tool_use":
            try:
                tool_use_block = next(block for block in response.content if block.type == "tool_use")
                tool_name = tool_use_block.name
                tool_args = tool_use_block.input
            except (StopIteration, AttributeError):
                yield FALLBACK_TOOL_PARSE_ERROR[lang]
                return

            try:
                result = execute_tool(tool_name, tool_args)
            except Exception:
                frappe.log_error(frappe.get_traceback(), f"ERP AI Tool Execution Error [{tool_name}]")
                yield FALLBACK_TOOL_EXEC_ERROR[lang]
                return

            tool_output = json.dumps(result, ensure_ascii=False, indent=2, default=str)

            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_block.id,
                        "content": tool_output
                    }
                ]
            })

            reply_language = lang
            presentation_instruction = f"""
ERP result data has been provided above for the user's query: "{message}".

Instructions:
1. Translate these raw ERP results into a clear, professional conversational sentence or short paragraph answering the user's question directly.
2. IMPORTANT: Write your entire reply in {reply_language}.
3. Never output raw JSON, dictionaries, or code blocks.
4. State currency and format numbers/dates clearly.
"""
            messages.append({"role": "user", "content": presentation_instruction})

            stream_kwargs = {
                "model": kwargs["model"],
                "max_tokens": 4096,
                "system": SYSTEM_PROMPT,
                "messages": messages,
            }
            if tools:
                stream_kwargs["tools"] = tools

            try:
                streamed_any_text = False
                with client.messages.stream(**stream_kwargs) as stream:
                    for text in stream.text_stream:
                        streamed_any_text = True
                        yield text

                if not streamed_any_text:
                    yield FALLBACK_PRESENTATION_ERROR[lang]
                return
            except Exception:
                frappe.log_error(frappe.get_traceback(), "ERP AI Presentation Streaming Error")
                yield FALLBACK_PRESENTATION_ERROR[lang]
                return

        text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        final_text = "".join(text_blocks).strip()

        if final_text:
            yield final_text
        else:
            yield FALLBACK_PRESENTATION_ERROR[lang]

    except Exception:
        frappe.log_error(frappe.get_traceback(), "ERP AI Critical System Error")
        yield FALLBACK_CRITICAL_ERROR[lang]

ask_ai = ask_claude