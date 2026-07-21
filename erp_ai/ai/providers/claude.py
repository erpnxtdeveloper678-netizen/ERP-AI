import json
import frappe
import anthropic
from erp_ai.ai.registry import get_functions
from erp_ai.ai.executor import execute_tool

def ask_claude(message: str, conversation=None):
    try:
        # 1. جلب إعدادات الذكاء الاصطناعي والمفتاح
        settings = frappe.get_single("AI Settings")
        api_key = settings.get_password("api_key")
        
        if not api_key:
            yield "عذراً، مفتاح الـ API غير مُعد بشكل صحيح في إعدادات النظام."
            return

        client = anthropic.Anthropic(api_key=api_key)
        
        # اختيار الموديل الافتراضي
        model_name = settings.model if settings.model and "claude" in settings.model else "claude-sonnet-5"

        # 2. تجهيز سجل المحادثة
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

        # 3. تجهيز الأدوات (Tools) المتاحة للنظام
        raw_functions = get_functions()
        tools = []
        if raw_functions:
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

        # 4. الـ System Prompt الصارم الذي يجبر المساعد على التنفيذ المباشر
        system_prompt = """
أنت مساعد ذكي ومحترف داخل نظام ERPNext وتمتلك أدوات تنفيذية كاملة (تتضمن القراءة، الإلغاء، الاعتماد، التحديث، والحذف) بناءً على صلاحيات المستخدم الفعلي.

قواعد صارمة ومطلقة لا يمكن مخالفتها:
1. ممنوع منعاً باتاً بناء أي جداول أو تقارير أو عرض بيانات في شكل Markdown tables إلا إذا طلب المستخدم صراحة بكلمات واضحة (مثل: "اعمل لي تقرير"، "هات جدول").
2. التزم حرفياً بالبيانات الخام المستخرجة دون أي تعديل لأسماء العملاء (مثل 'k').
3. إذا طلب المستخدم أي إجراء تنفيذي على المستندات (مثل: الغيها، اعتمدها، احذفها، عدلها): يجب عليك فوراً ودون تردد استخدام الأداة التنفيذية المتاحة لديك (مثل manage_erp_document) لتنفيذ الطلب في الخلفية فوراً، ولا تقل أبداً أنك لا تملك صلاحية أو أن صلاحياتك تقتصر على القراءة فقط طالما أن الأدوات متاحة لك.
4. الأسلوب: أجب دائماً بنفس اللغة التي يتحدث بها المستخدم.
"""

        kwargs = {
            "model": model_name,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        # 5. إرسال الطلب الأولي لـ Anthropic مع معالجة أخطاء الموديل
        try:
            response = client.messages.create(**kwargs)
        except anthropic.NotFoundError:
            kwargs["model"] = "claude-sonnet-4-6"
            response = client.messages.create(**kwargs)
        except Exception as api_err:
            frappe.log_error(frappe.get_traceback(), "ERP AI Anthropic API Error")
            yield "عذراً، حدث خطأ أثناء الاتصال بخدمة الذكاء الاصطناعي."
            return

        # 6. معالجة استخدام الأدوات (Tool Use)
        if response.stop_reason == "tool_use":
            try:
                tool_use_block = next(block for block in response.content if block.type == "tool_use")
                tool_name = tool_use_block.name
                tool_args = tool_use_block.input
            except (StopIteration, AttributeError):
                yield "عذراً، حدث خطأ في استخلاص بيانات الأداة المطلوبة."
                return

            # تنفيذ الأداة مع حماية الأخطاء
            try:
                result = execute_tool(tool_name, tool_args)
            except Exception as tool_err:
                frappe.log_error(frappe.get_traceback(), f"ERP AI Tool Execution Error [{tool_name}]")
                yield f"عذراً، حدث خطأ أثناء تنفيذ الطلب: {str(tool_err)}"
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

            # 7. توجيه العرض الذكي
            presentation_instruction = f"""
ERP Result Data provided above. Answer the user's original question: "{message}" based strictly on the ERP data.

Strict Presentation Rules:
1. NEVER output a Markdown table or report format UNLESS the user's original query explicitly requested a report, table, or breakdown.
2. If it's a general query, details check, or action result (such as document cancellation, submission, or update) that does NOT explicitly request a table: Answer in clean, professional conversational text.
3. NEVER alter any customer name, string, or raw value from the ERP data.
4. Keep the tone executive, precise, and highly professional in the user's language.
"""
            messages.append({"role": "user", "content": presentation_instruction})

            stream_kwargs = {
                "model": kwargs["model"],
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": messages,
            }
            if tools:
                stream_kwargs["tools"] = tools

            # البث المباشر للرد بعد تنفيذ الأداة
            try:
                with client.messages.stream(**stream_kwargs) as stream:
                    for text in stream.text_stream:
                        yield text
                return
            except Exception as stream_err:
                frappe.log_error(frappe.get_traceback(), "ERP AI Stream Error")
                yield "عذراً، حدث خطأ أثناء توليد الرد النهائي."
                return

        # 8. الرد المباشر في حال عدم طلب استخدام أداة (دردشة مباشرة)
        try:
            with client.messages.stream(
                model=kwargs["model"],
                max_tokens=4096,
                system=system_prompt,
                messages=messages
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as direct_err:
            frappe.log_error(frappe.get_traceback(), "ERP AI Direct Stream Error")
            yield "عذراً، حدث خطأ غير متوقع أثناء معالجة رد المساعد."

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "ERP AI Critical System Error")
        yield f"حدث خطأ بالنظام الداخلي للمساعد: {str(e)}"