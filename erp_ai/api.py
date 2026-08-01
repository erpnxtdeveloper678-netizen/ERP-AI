import json
import frappe
import anthropic

DEFAULT_MODEL = "claude-sonnet-5"

REPORT_TRIGGER_KEYWORDS = [
    "report", "تقرير", "report builder", "query report", "script report",
    "dashboard", "لوحة تحكم", "داشبورد", "لوحه تحكم"
]

GENERIC_ERROR_MESSAGE = {
    "English": "Sorry, an unexpected error occurred while processing your request. Please try again.",
    "Arabic": "عذراً، حدث خطأ غير متوقع أثناء معالجة طلبك. برجاء المحاولة مرة أخرى.",
}
EMPTY_REPLY_MESSAGE = {
    "English": "Sorry, no reply was received from the assistant. Please try rephrasing your question or try again.",
    "Arabic": "عذراً، لم يتم استلام رد من المساعد الذكي. برجاء إعادة صياغة سؤالك أو المحاولة مرة أخرى.",
}

PENDING_MARKER_PREFIX = "<!--ERP_AI_PENDING_ACTION:"
PENDING_MARKER_SUFFIX = "-->"

AFFIRMATIVE_WORDS = [
    "yes", "yeah", "yep", "confirm", "confirmed", "sure", "ok", "okay", "go ahead", "do it",
    "نعم", "ايوه", "أيوه", "اه", "آه", "تمام", "أكد", "اكد", "موافق", "اعمل", "أعمل", "أنشئ", "انشئ"
]
NEGATIVE_WORDS = [
    "no", "nope", "cancel", "don't", "dont", "stop",
    "لا", "لأ", "الغاء", "إلغاء", "الغي", "مش عايز", "متعملش", "لا تفعل"
]

CLASSIFY_TOOL = {
    "name": "classify_request",
    "description": (
        "Classify the user's ERP assistant request as a normal chat, or an explicit request "
        "to permanently create a Report (Report Builder, Query Report, or Script Report) "
        "or a Dashboard record in the ERPNext system."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["chat", "create_report", "create_dashboard"],
            },
            "report_type": {
                "type": "string",
                "enum": ["Report Builder", "Query Report", "Script Report"],
                "description": "Specific type of report if action is create_report. Default to Report Builder if ambiguous.",
            },
            "report_title": {
                "type": "string",
                "description": "Only set if action is create_report.",
            },
            "ref_doctype": {
                "type": "string",
                "description": "The ERPNext DocType this report or dashboard should be based on (e.g., 'Sales Invoice').",
            },
            "module": {
                "type": "string",
                "description": "The ERPNext module this report or dashboard belongs to, e.g. 'Accounts', 'Selling'.",
            },
            "query_text": {
                "type": "string",
                "description": "SQL query text if the report_type is Query Report.",
            },
            "dashboard_name": {
                "type": "string",
                "description": "Only set if action is create_dashboard.",
            },
            "target_doctype": {
                "type": "string",
                "description": "Target DocType for analytical visuals when creating a dashboard (e.g. Sales Invoice).",
            }
        },
        "required": ["action"],
    },
}

CLASSIFY_SYSTEM_PROMPT = """
You are an intent classifier for an ERPNext AI assistant. Your ONLY job is to decide whether the user's message is:

- "chat": a normal question, data inquiry, or request to see analytics inside the chat interface.
- "create_report": an explicit request to permanently create and save a new Report record in the ERPNext system.
- "create_dashboard": an explicit request to permanently create and save a new Dashboard record with cards and charts in the ERPNext system.

Default to "chat" whenever it's ambiguous.
"""


def _detect_lang(text: str) -> str:
    if not text:
        return "English"
    for ch in text:
        if "\u0600" <= ch <= "\u06FF":
            return "Arabic"
    return "English"


def trim_chat_history(history, max_messages=15):
    if not history or not isinstance(history, list):
        return []
    if len(history) > max_messages:
        return history[-max_messages:]
    return history


def _extract_pending_confirmation(conversation):
    if not conversation:
        return None
    for msg in reversed(conversation):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "")
        if not isinstance(content, str):
            continue
        start = content.find(PENDING_MARKER_PREFIX)
        if start == -1:
            return None
        end = content.find(PENDING_MARKER_SUFFIX, start)
        if end == -1:
            return None
        raw = content[start + len(PENDING_MARKER_PREFIX):end]
        try:
            return json.loads(raw)
        except Exception:
            return None
    return None


def _is_affirmative(text: str) -> bool:
    lowered = (text or "").strip().lower()
    return any(word in lowered for word in AFFIRMATIVE_WORDS)


def _is_negative(text: str) -> bool:
    lowered = (text or "").strip().lower()
    return any(word in lowered for word in NEGATIVE_WORDS)


def _build_pending_marker(payload: dict) -> str:
    return f"{PENDING_MARKER_PREFIX}{json.dumps(payload, ensure_ascii=False)}{PENDING_MARKER_SUFFIX}"


def _get_ai_client_and_model():
    settings = frappe.get_single("AI Settings")
    api_key = settings.get_password("api_key")
    if not api_key:
        return None, None
    client = anthropic.Anthropic(api_key=api_key)
    model_name = settings.model if settings.model and "claude" in settings.model else DEFAULT_MODEL
    return client, model_name


def _classify_intent(message: str):
    try:
        client, model_name = _get_ai_client_and_model()
        if not client:
            return {"action": "chat"}

        response = client.messages.create(
            model=model_name,
            max_tokens=300,
            system=CLASSIFY_SYSTEM_PROMPT,
            tools=[CLASSIFY_TOOL],
            tool_choice={"type": "tool", "name": "classify_request"},
            messages=[{"role": "user", "content": message}],
        )
        block = next((b for b in response.content if b.type == "tool_use"), None)
        if block and isinstance(block.input, dict):
            return block.input
    except Exception:
        frappe.log_error(frappe.get_traceback(), "ERP AI Intent Classification Error")

    return {"action": "chat"}


def _propose_report_creation(intent: dict, full_message: str, conversation, lang: str):
    report_title = (intent.get("report_title") or "").strip()
    report_type = (intent.get("report_type") or "Report Builder").strip()
    ref_doctype = (intent.get("ref_doctype") or "").strip()
    module = (intent.get("module") or "Accounts").strip()
    query_text = (intent.get("query_text") or "").strip()

    if not report_title:
        return call_ai_service(full_message, conversation)

    if not frappe.has_permission("Report", "create"):
        msg = "You don't have permission to create reports." if lang == "English" else "ليس لديك صلاحية إنشاء تقارير في النظام."
        return {"reply": msg}

    marker = _build_pending_marker({
        "type": "create_report",
        "report_title": report_title,
        "report_type": report_type,
        "ref_doctype": ref_doctype,
        "module": module,
        "query_text": query_text,
    })

    confirmation_text = (
        f"I'd like to create a saved **{report_type}**:\n- **Title:** {report_title}\n- **Module:** {module}\n" +
        (f"- **Based on:** {ref_doctype}\n" if report_type == "Report Builder" else "") +
        (f"- **SQL Query:** `{query_text}`\n" if query_text else "") +
        f"\nShall I create it? (yes/no)"
        if lang == "English" else
        f"عايز أنشئ تقرير من نوع **{report_type}**:\n- **الاسم:** {report_title}\n- **الموديول:** {module}\n" +
        (f"- **مبني على:** {ref_doctype}\n" if report_type == "Report Builder" else "") +
        (f"- **استعلام SQL:** `{query_text}`\n" if query_text else "") +
        f"\nأأكد الإنشاء؟ (أيوه/لأ)"
    )
    return {"reply": f"{confirmation_text}\n\n{marker}"}


def _propose_dashboard_creation(intent: dict, full_message: str, conversation, lang: str):
    dashboard_name = (intent.get("dashboard_name") or "").strip()
    module = (intent.get("module") or "Accounts").strip()
    target_doctype = (intent.get("target_doctype") or intent.get("ref_doctype") or "Sales Invoice").strip()

    if not dashboard_name:
        return call_ai_service(full_message, conversation)

    if not frappe.has_permission("Dashboard", "create"):
        msg = "You don't have permission to create dashboards." if lang == "English" else "ليس لديك صلاحية إنشاء لوحات تحكم."
        return {"reply": msg}

    marker = _build_pending_marker({
        "type": "create_dashboard",
        "dashboard_name": dashboard_name,
        "module": module,
        "target_doctype": target_doctype
    })

    confirmation_text = (
        f"I'd like to create a rich Dashboard:\n- **Name:** {dashboard_name}\n- **Module:** {module}\n- **Target DocType:** {target_doctype}\n\nShall I create it with custom cards and charts? (yes/no)"
        if lang == "English" else
        f"عايز أنشئ لوحة تحكم (Dashboard) متكاملة:\n- **الاسم:** {dashboard_name}\n- **الموديول:** {module}\n- **المستند المستهدف:** {target_doctype}\n\nأأكد الإنشاء مع إضافة الرسومات البيانية والبطاقات الإحصائية؟ (أيوه/لأ)"
    )
    return {"reply": f"{confirmation_text}\n\n{marker}"}


def _execute_pending_action(pending: dict, lang: str):
    action_type = pending.get("type")

    if action_type == "create_report":
        from erp_ai.ai.registry import create_erp_report
        res = create_erp_report(
            report_title=pending.get("report_title"),
            report_type=pending.get("report_type", "Report Builder"),
            ref_doctype=pending.get("ref_doctype"),
            module=pending.get("module"),
            query_text=pending.get("query_text")
        )
        return {"reply": res.get("message")}
    elif action_type == "create_dashboard":
        from erp_ai.ai.registry import create_erp_dashboard
        res = create_erp_dashboard(
            dashboard_name=pending.get("dashboard_name"),
            module=pending.get("module"),
            target_doctype=pending.get("target_doctype", "Sales Invoice")
        )
        return {"reply": res.get("message")}

    return {"reply": "Unknown action."}


@frappe.whitelist()
def ask(message, conversation=None, file_data=None, file_name=None, conversation_name=None):
    if conversation:
        try:
            conversation = json.loads(conversation)
        except Exception:
            conversation = []
    else:
        conversation = []

    trimmed_conversation = trim_chat_history(conversation)
    full_message = message or ""
    
    if file_data:
        full_message = f"[Attached File: {file_name}]\nFile Content:\n{file_data}\n\nUser Question:\n{full_message}"
        res = call_ai_service(full_message, trimmed_conversation)
    else:
        lang = _detect_lang(full_message)
        pending = _extract_pending_confirmation(trimmed_conversation)

        if pending:
            if _is_affirmative(full_message):
                res = _execute_pending_action(pending, lang)
            elif _is_negative(full_message):
                msg = "No problem." if lang == "English" else "تمام، تم إلغاء الطلب ولا يهمك."
                res = {"reply": msg}
            else:
                res = call_ai_service(full_message, trimmed_conversation)
        else:
            lower_message = full_message.lower()
            looks_like_request = any(kw in lower_message for kw in REPORT_TRIGGER_KEYWORDS)

            if looks_like_request:
                intent = _classify_intent(full_message)
                action = intent.get("action")
                if action == "create_report":
                    res = _propose_report_creation(intent, full_message, trimmed_conversation, lang)
                elif action == "create_dashboard":
                    res = _propose_dashboard_creation(intent, full_message, trimmed_conversation, lang)
                else:
                    res = call_ai_service(full_message, trimmed_conversation)
            else:
                res = call_ai_service(full_message, trimmed_conversation)

    try:
        updated_conversation = list(conversation)
        updated_conversation.append({"role": "user", "content": full_message})
        updated_conversation.append({"role": "assistant", "content": res.get("reply", "")})

        save_res = save_conversation(conversation_name=conversation_name, messages=updated_conversation)
        if save_res.get("status") == "success":
            res["conversation_name"] = save_res.get("name")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Auto Save Conversation Error")

    return res


def call_ai_service(message, conversation):
    lang = _detect_lang(message)
    reply = ""

    try:
        from erp_ai.ai.service import ask_ai
        response_generator = ask_ai(message=message, conversation=conversation)
        if hasattr(response_generator, "__iter__") and not isinstance(response_generator, (str, dict, list)):
            reply = "".join([str(chunk) for chunk in response_generator if chunk])
        else:
            reply = str(response_generator or "")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "ERP AI API Error")
        reply = GENERIC_ERROR_MESSAGE[lang]

    if not reply or not reply.strip():
        reply = EMPTY_REPLY_MESSAGE[lang]

    return {"reply": reply}


@frappe.whitelist()
def save_conversation(conversation_name=None, title=None, messages=None):
    try:
        if isinstance(messages, str):
            messages_list = json.loads(messages)
            messages_json = messages
        else:
            messages_list = messages or []
            messages_json = json.dumps(messages_list, ensure_ascii=False)

        if not title and messages_list:
            first_msg = next((m.get("content") for m in messages_list if m.get("role") == "user"), "New Conversation")
            title = (first_msg[:30] + "...") if len(first_msg) > 30 else first_msg

        if conversation_name and frappe.db.exists("AI Conversation", conversation_name):
            doc = frappe.get_doc("AI Conversation", conversation_name)
            doc.messages = messages_json
            doc.last_activity = frappe.utils.now_datetime()
            if title:
                doc.title = title
            # الحفظ هنا مسموح للـ Chat Document التابع للنظام
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            return {"status": "success", "name": doc.name}
        else:
            doc = frappe.get_doc({
                "doctype": "AI Conversation",
                "title": title or "New Conversation",
                "user": frappe.session.user,
                "status": "Open",
                "started_on": frappe.utils.now_datetime(),
                "last_activity": frappe.utils.now_datetime(),
                "messages": messages_json
            })
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            return {"status": "success", "name": doc.name}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Save Conversation Error")
        return {"status": "error", "message": "Could not save conversation."}


@frappe.whitelist()
def get_user_conversations():
    try:
        conversations = frappe.get_list(
            "AI Conversation",
            filters={"user": frappe.session.user},
            fields=["name", "title", "modified", "status"],
            order_by="modified desc",
            limit_page_length=20
        )
        return {"status": "success", "data": conversations}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Get User Conversations Error")
        return {"status": "error", "data": []}


@frappe.whitelist()
def load_conversation(conversation_name):
    try:
        if not frappe.db.exists("AI Conversation", conversation_name):
            return {"status": "error", "message": "Conversation not found."}

        doc = frappe.get_doc("AI Conversation", conversation_name)
        
        # التأكد من أن المحادثة ملك للمستخدم الحالي فقط لحماية الخصوصية
        if doc.user != frappe.session.user and frappe.session.user != "Administrator":
            return {"status": "error", "message": "Access Denied."}

        messages = []
        if doc.messages:
            if isinstance(doc.messages, str):
                messages = json.loads(doc.messages)
            elif isinstance(doc.messages, list):
                messages = doc.messages

        return {
            "status": "success",
            "name": doc.name,
            "title": doc.title,
            "messages": messages
        }
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Load Conversation Error")
        return {"status": "error", "message": "Could not load conversation.", "messages": []}


@frappe.whitelist()
def delete_conversation(conversation_name):
    try:
        if conversation_name and frappe.db.exists("AI Conversation", conversation_name):
            doc = frappe.get_doc("AI Conversation", conversation_name)
            if doc.user == frappe.session.user or frappe.session.user == "Administrator":
                frappe.delete_doc("AI Conversation", conversation_name, ignore_permissions=True)
                frappe.db.commit()
                return {"status": "success", "message": "Conversation deleted successfully."}
            else:
                return {"status": "error", "message": "Permission Denied."}
        return {"status": "error", "message": "Conversation not found."}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Delete Conversation Error")
        return {"status": "error", "message": "Could not delete conversation."}