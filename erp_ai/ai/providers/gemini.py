import json
import frappe
from google import genai
from google.genai import types

from erp_ai.ai.registry import get_functions
from erp_ai.ai.executor import execute_tool


def _normalize_args(args):
    if args is None:
        return {}
    if isinstance(args, dict):
        return args
    try:
        return json.loads(json.dumps(dict(args)))
    except Exception:
        pass
    return {}


def _build_messages(message, conversation=None):
    messages = []
    if conversation:
        try:
            if isinstance(conversation, str):
                conversation = json.loads(conversation)
            for msg in conversation:
                role = msg.get("role", "user")
                if role == "assistant":
                    role = "model"
                messages.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg.get("content", ""))]
                    )
                )
        except Exception:
            pass

    messages.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=message)]
        )
    )
    return messages


def ask_gemini(message: str, conversation=None):
    """
    الدالة الأساسية المسؤولة عن الـ Streaming وبث النصوص حتة حتة (yield)
    مؤمنة بالكامل ومحدثة لتوليد تقارير مالية احترافية وتنفيذية بناءً على سؤال المستخدم فقط.
    """
    try:
        settings = frappe.get_single("AI Settings")
        api_key = settings.get_password("api_key")

        if not api_key:
            yield "API Key is missing."
            return

        client = genai.Client(
            api_key=api_key,
            http_options={'api_version': 'v1alpha'}
        )

        model_name = settings.model or "gemini-2.5-flash"
        raw_functions = get_functions()
        tools_list = [{"function_declarations": [f for f in raw_functions]}] if raw_functions else None
        
        # تجهيز الـ config الموحد وتوجيه الموديل بأسلوب احترافي ومحلل مالي ذكي
        gen_config = types.GenerateContentConfig(
            tools=tools_list,
            system_instruction="""
أنت محلل بيانات مالي ومساعد ذكي مدمج داخل نظام ERPNext (تتحدث بلهجة مهنية، واضحة، ومباشرة بدون مقدمات إنشائية).
إذا طلب المستخدم تحليل مبيعات أو مقارنة عملاء: استخدم أداة 'analyze_data' مع (operation: "group", group_by: "customer", field: "grand_total", aggregate: "sum").
إذا كان السؤال عن أكبر أو أقل فاتورة أو استعلام محدد: استخدم الأداة المناسبة بدقة (مثل run_erp_query أو عمليات max/min) بناءً على ما يخدم السؤال فقط.
أجب دائماً باللغة التي يتحدث بها المستخدم.
"""
        )

        messages = _build_messages(message, conversation)

        # أول استدعاء للموديل لمعرفة هل سيحتاج أداة أم لا
        response = client.models.generate_content(
            model=model_name,
            contents=messages,
            config=gen_config
        )

        function_calls = response.function_calls
        if function_calls:
            function_call = function_calls[0]
            tool_name = function_call.name
            tool_args = _normalize_args(function_call.args)

            try:
                result = execute_tool(tool_name, tool_args)
            except Exception:
                yield f"Error executing tool: {frappe.get_traceback()}"
                return

            tool_output = json.dumps(result, ensure_ascii=False, indent=2, default=str) if isinstance(result, (dict, list)) else str(result)

            messages.append(types.Content(role="model", parts=[types.Part.from_text(text=f"The tool '{tool_name}' was executed successfully.")]))
            messages.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"""
ERP Result Data:
{tool_output}

Answer the user's last question based directly on the ERP data provided above.
Strict Professional Presentation Rules:
1. Format your response clean and structured. Use Bold text for key insights and numbers.
2. If the data contains multiple records or a breakdown, ALWAYS present it in a beautifully formatted Markdown table with clear headers.
3. Answer ONLY what the user asked. Do not add generic conclusions or irrelevant logic (e.g., do not talk about "most active customer" unless specifically asked about activity).
4. Keep the tone executive, precise, and highly professional (Executive Summary style).
5. Always reply in the same language the user is using (Arabic or English).
""")]
                )
            )

            response_stream = client.models.generate_content_stream(model=model_name, contents=messages)
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
            return

        # إذا لم يستدعِ أداة، يتم تشغيل الستريم العادي
        response_stream = client.models.generate_content_stream(
            model=model_name, 
            contents=messages,
            config=gen_config
        )
        for chunk in response_stream:
            if chunk.text:
                yield chunk.text

    except Exception:
        yield frappe.get_traceback()