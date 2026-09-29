import json
import time
import frappe
from google import genai
from google.genai import types
from google.genai import errors

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


def _build_gemini_system_instruction(page_context=None):
    base = """
أنت محلل بيانات مالي ومساعد ذكي مدمج داخل نظام ERPNext (تتحدث بلهجة مهنية، واضحة، ومباشرة بدون مقدمات إنشائية).
جميع الأدوات مقيدة تلقائياً بصلاحيات المستخدم الحالي في ERPNext - لا تحاول تجاوز رسالة "permission" إذا ظهرت.

مهم جدًا - DocTypes مخصصة (Custom): النظام ده غالبًا فيه أنواع مستندات خاصة بيها (custom DocTypes) اتعملت خصيصًا لطبيعة عمل الشركة دي، ومش هتلاقيها في تدريبك العادي لأنها بتختلف من نظام لنظام. لو المستخدم ذكر نوع سجل أو مصطلح عمل مش عارفه، **متفترضش إنه مش موجود** - استخدم أداة 'find_doctype' الأول بكلمات من كلامه. لو رجعلك نتيجة، تعامل معاه بنفس الطريقة العادية (get_doctype_meta لمعرفة الحقول، وبعدين list_documents/get_document/create_document حسب الحاجة) - كل الأدوات العامة بتشتغل مع أي DocType عادي أو مخصص من غير فرق. قول للمستخدم إن الحاجة دي مش موجودة بس لو 'find_doctype' رجع فاضي فعلاً.

- لتحليل مبيعات أو مقارنة عملاء: استخدم أداة 'analyze_data' مع (operation: "group", group_by: "customer", field: "grand_total", aggregate: "sum").
- لأكبر/أقل قيمة (فاتورة، طلب...): استخدم 'analyze_data' مع (operation: "max" أو "min", field: "grand_total").
- لعرض قائمة سجلات مفلترة: استخدم 'list_documents'. لسجل واحد بالاسم: استخدم 'get_document'.
- لإنشاء سجل جديد: استخدم 'create_document' (استعلم أولاً عبر 'get_doctype_meta' إذا لم تكن متأكداً من أسماء الحقول).
- لإنشاء تقرير محفوظ: استخدم 'create_report'. لإنشاء رسم بياني: استخدم 'create_dashboard_chart'. لتجميع الرسوم في لوحة تحكم: استخدم 'create_dashboard'.

أجب دائماً باللغة التي يتحدث بها المستخدم.
"""
    if page_context and isinstance(page_context, dict):
        doctype = page_context.get("doctype")
        docname = page_context.get("docname")
        route = page_context.get("route")
        if doctype or route:
            extra = "\n\nالصفحة اللي المستخدم فاتحها دلوقتي في المتصفح (معلومة إرشادية بس - لو محتاج تتأكد من البيانات الفعلية استخدم get_document):"
            if route:
                extra += f"\n- المسار: {route}"
            if doctype:
                extra += f"\n- نوع المستند (DocType): {doctype}"
            if docname:
                extra += f"\n- اسم المستند: {docname}"
            extra += "\nلو المستخدم قال \"المستند ده\" أو \"الصفحة دي\" من غير ما يحدد اسم، يبقى قصده المستند اللي فوق."
            base = base + extra
    return base


def ask_gemini(message: str, conversation=None, page_context=None):
    """
    الدالة الإنتاجية النهائية للعمل مع المفتاح المدفوع وآلية Retry ذكية
    """
    try:
        settings = frappe.get_single("AI Settings")
        api_key = settings.get_password("api_key")

        if not api_key:
            yield "API Key is missing."
            return

        client = genai.Client(api_key=api_key)

        model_name = settings.model or "gemini-1.5-pro"
        raw_functions = get_functions(provider="gemini")
        tools_list = [{"function_declarations": [f for f in raw_functions]}] if raw_functions else None
        
        gen_config = types.GenerateContentConfig(
            tools=tools_list,
            system_instruction=_build_gemini_system_instruction(page_context)
        )

        messages = _build_messages(message, conversation)

        max_retries = 5
        delay = 2
        response = None

        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=messages,
                    config=gen_config
                )
                break
            except (errors.ServerError, errors.APIError) as e:
                if e.code in [503, 429] and attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise e

        function_calls = response.function_calls if response else None
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

            delay = 2
            for attempt in range(max_retries):
                try:
                    response_stream = client.models.generate_content_stream(model=model_name, contents=messages)
                    for chunk in response_stream:
                        if chunk.text:
                            yield chunk.text
                    return
                except (errors.ServerError, errors.APIError) as e:
                    if e.code in [503, 429] and attempt < max_retries - 1:
                        time.sleep(delay)
                        delay *= 2
                    else:
                        raise e

        response_stream = client.models.generate_content_stream(
            model=model_name, 
            contents=messages, 
            config=gen_config
        )
        for chunk in response_stream:
            if chunk.text:
                yield chunk.text

    except (errors.ServerError, errors.APIError) as e:
        if e.code == 503:
            yield "⚠️ خوادم ذكاء جوجل تواجه ضغطاً مرتفعاً، جاري إعادة المحاولة..."
        elif e.code == 429:
            yield "⚠️ تم بلوغ الحد الأقصى المؤقت للطلبات المدفوعة، يتم الانتظار قليلاً..."
        else:
            yield f"⚠️ خطأ بالاتصال: {e.message}"

    except Exception:
        yield f"حدث خطأ غير متوقع:\n {frappe.get_traceback()}"
        