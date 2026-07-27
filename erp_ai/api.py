import json
import frappe
import anthropic
import csv
import io


DEFAULT_MODEL = "claude-sonnet-5"

# Keywords that MIGHT indicate the user wants a permanently saved system
# Report (as opposed to just wanting to see data/a table in the chat).
# Only when one of these appears do we pay the cost of an extra classification
# call — everything else skips straight to a normal chat reply.
REPORT_TRIGGER_KEYWORDS = ["report", "تقرير", "report builder"]

GENERIC_ERROR_MESSAGE = {
    "English": "Sorry, an unexpected error occurred while processing your request. Please try again.",
    "Arabic": "عذراً، حدث خطأ غير متوقع أثناء معالجة طلبك. برجاء المحاولة مرة أخرى.",
}
EMPTY_REPLY_MESSAGE = {
    "English": "Sorry, no reply was received from the assistant. Please try rephrasing your question or try again.",
    "Arabic": "عذراً، لم يتم استلام رد من المساعد الذكي. برجاء إعادة صياغة سؤالك أو المحاولة مرة أخرى.",
}

# Hidden marker embedded in a confirmation-prompt reply so we can recognise,
# statelessly, that the user's NEXT message is answering a pending
# report-creation confirmation (we just re-read it back out of the
# conversation history the frontend already sends with every request).
PENDING_MARKER_PREFIX = "<!--ERP_AI_PENDING_REPORT:"
PENDING_MARKER_SUFFIX = "-->"

AFFIRMATIVE_WORDS = [
    "yes", "yeah", "yep", "confirm", "confirmed", "sure", "ok", "okay", "go ahead", "do it",
    "نعم", "ايوه", "أيوه", "اه", "آه", "تمام", "أكد", "اكد", "موافق", "اعمل", "أعمل",
]
NEGATIVE_WORDS = [
    "no", "nope", "cancel", "don't", "dont", "stop",
    "لا", "لأ", "الغاء", "إلغاء", "الغي", "مش عايز", "متعملش",
]

CLASSIFY_TOOL = {
    "name": "classify_request",
    "description": (
        "Classify the user's ERP assistant request as either a normal chat/data "
        "query, or an explicit request to permanently create and save a new "
        "Report record in the ERPNext system."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["chat", "create_report"],
            },
            "report_title": {
                "type": "string",
                "description": "Only set if action is create_report.",
            },
            "ref_doctype": {
                "type": "string",
                "description": (
                    "The ERPNext DocType this report should be based on, e.g. "
                    "'Sales Invoice'. Only set if action is create_report."
                ),
            },
            "module": {
                "type": "string",
                "description": (
                    "The ERPNext module this report belongs to, e.g. 'Accounts'. "
                    "Only set if action is create_report."
                ),
            },
        },
        "required": ["action"],
    },
}

CLASSIFY_SYSTEM_PROMPT = """
You are an intent classifier for an ERPNext AI assistant. Your ONLY job is to decide whether the user's message is:

- "chat": a normal question, or a request to see data/analysis/a report inside the conversation. If the user just wants to *see* numbers or a table right now, this is "chat" — even if they use the word "report".
- "create_report": an explicit, unambiguous request to permanently create and save a new Report record in the ERPNext system itself (e.g. "create a saved report called X", "save this as a report in the system", "add this to the Reports list").

Default to "chat" whenever it's ambiguous. Only classify as "create_report" when the user clearly wants a persistent system Report object created — not just a table or summary shown to them right now.

Always call the classify_request tool with your decision. Never reply with plain text.
"""


def _detect_lang(text: str) -> str:
    """Small heuristic: Arabic-script characters -> Arabic, else English."""
    if not text:
        return "English"
    for ch in text:
        if "\u0600" <= ch <= "\u06FF":
            return "Arabic"
    return "English"


def _extract_pending_confirmation(conversation):
    """
    Looks at the most recent assistant message in the conversation history
    for a hidden pending-report marker, and returns the embedded dict if
    found, else None. This makes confirmation stateless — no DB/session
    storage needed, since the frontend already resends full history.
    """
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
            return None  # most recent assistant turn wasn't a pending confirmation
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
    """Returns (client, model_name) or (None, None) if not configured.

    NOTE: this function was missing from the original file, which meant
    _classify_intent() always hit a NameError, was silently swallowed by
    its own try/except, and therefore *every* "create a report" request
    silently fell back to {"action": "chat"} — the report-creation feature
    never actually ran, with no visible error to the user.
    """
    settings = frappe.get_single("AI Settings")
    api_key = settings.get_password("api_key")
    if not api_key:
        return None, None
    client = anthropic.Anthropic(api_key=api_key)
    model_name = settings.model if settings.model and "claude" in settings.model else DEFAULT_MODEL
    return client, model_name


def _classify_intent(message: str):
    """
    Uses forced tool-calling (not free-text JSON) so the response is always
    a valid structured object, with zero conflict against the main
    assistant's "never output raw JSON" system prompt — this is a fully
    separate, minimal call dedicated only to classification.
    """
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
    """
    Validates the extracted report details and, if everything checks out,
    returns a CONFIRMATION PROMPT (with a hidden pending marker) instead of
    creating anything yet. Nothing is written to the database at this stage.
    """
    report_title = (intent.get("report_title") or "").strip()
    ref_doctype = (intent.get("ref_doctype") or "").strip()
    module = (intent.get("module") or "").strip()

    # If the model didn't confidently extract everything needed, don't guess —
    # fall back to a normal conversational reply instead.
    if not report_title or not ref_doctype or not module:
        return call_ai_service(full_message, conversation)

    if not frappe.db.exists("DocType", ref_doctype):
        msg = (
            f"I can create a report, but '{ref_doctype}' isn't a valid DocType in this system. "
            f"Could you confirm the correct one?"
            if lang == "English" else
            f"يمكنني إنشاء التقرير، لكن '{ref_doctype}' ليس نوع مستند (DocType) صحيح في النظام. "
            f"هل يمكنك تأكيد الاسم الصحيح؟"
        )
        return {"reply": msg}

    if not frappe.db.exists("Module Def", module):
        msg = (
            f"I can create a report, but '{module}' isn't a valid module in this system."
            if lang == "English" else
            f"يمكنني إنشاء التقرير، لكن '{module}' ليس موديول صحيح في النظام."
        )
        return {"reply": msg}

    if not frappe.has_permission("Report", "create"):
        msg = (
            "You don't have permission to create reports in this system. "
            "Please contact your administrator."
            if lang == "English" else
            "ليس لديك صلاحية إنشاء تقارير في هذا النظام. برجاء التواصل مع مسؤول النظام."
        )
        return {"reply": msg}

    if frappe.db.exists("Report", {"report_name": report_title}):
        msg = (
            f"A report named '{report_title}' already exists in the system."
            if lang == "English" else
            f"يوجد بالفعل تقرير باسم '{report_title}' في النظام."
        )
        return {"reply": msg}

    # Be upfront that column layout still needs manual setup — a bare Report
    # Builder record has no columns/sorting/filters yet, so it won't show
    # "top X" style results until configured in the Report Builder UI.
    marker = _build_pending_marker({
        "report_title": report_title,
        "ref_doctype": ref_doctype,
        "module": module,
    })

    if lang == "English":
        confirmation_text = (
            f"I'd like to create a saved Report in the system:\n\n"
            f"- **Title:** {report_title}\n"
            f"- **Based on:** {ref_doctype}\n"
            f"- **Module:** {module}\n\n"
            f"Note: it will be created as an empty Report Builder — you'll still need to "
            f"open it and add/arrange the specific columns, sorting, and filters afterward.\n\n"
            f"Shall I go ahead and create it? (yes/no)"
        )
    else:
        confirmation_text = (
            f"عايز أنشئ تقرير محفوظ في النظام بالتفاصيل دي:\n\n"
            f"- **الاسم:** {report_title}\n"
            f"- **مبني على:** {ref_doctype}\n"
            f"- **الموديول:** {module}\n\n"
            f"ملحوظة: هيتحفظ كـ Report Builder فاضي، وهتحتاج تفتحه بعد كده وتضيف/ترتب الأعمدة والفلاتر المطلوبة بنفسك.\n\n"
            f"أأكد الإنشاء؟ (أيوه/لأ)"
        )

    return {"reply": f"{confirmation_text}\n\n{marker}"}


def _create_report_now(pending: dict, lang: str):
    """
    Performs the actual creation, re-validating everything (state may have
    changed between the proposal and the confirmation).
    """
    report_title = (pending.get("report_title") or "").strip()
    ref_doctype = (pending.get("ref_doctype") or "").strip()
    module = (pending.get("module") or "").strip()

    if not report_title or not ref_doctype or not module:
        msg = (
            "Sorry, I lost track of the report details — could you ask again?"
            if lang == "English" else
            "عذراً، فقدت تفاصيل التقرير — ممكن تطلب تاني؟"
        )
        return {"reply": msg}

    if not frappe.db.exists("DocType", ref_doctype) or not frappe.db.exists("Module Def", module):
        msg = (
            "Sorry, the DocType or module is no longer valid. Please try again."
            if lang == "English" else
            "عذراً، الـ DocType أو الموديول لم يعودا صحيحين. برجاء المحاولة مرة أخرى."
        )
        return {"reply": msg}

    if not frappe.has_permission("Report", "create"):
        msg = (
            "You don't have permission to create reports in this system."
            if lang == "English" else
            "ليس لديك صلاحية إنشاء تقارير في هذا النظام."
        )
        return {"reply": msg}

    try:
        if frappe.db.exists("Report", {"report_name": report_title}):
            msg = (
                f"A report named '{report_title}' already exists in the system."
                if lang == "English" else
                f"يوجد بالفعل تقرير باسم '{report_title}' في النظام."
            )
            return {"reply": msg}

        doc = frappe.get_doc({
            "doctype": "Report",
            "report_name": report_title,
            "ref_doctype": ref_doctype,
            "report_type": "Report Builder",
            "is_standard": "No",
            "module": module,
        })
        doc.insert()  # respects the current user's permissions

        msg = (
            f"✅ Report '{report_title}' was created for {ref_doctype} in the {module} module. "
            f"Open it from the Reports list to set up its columns and filters."
            if lang == "English" else
            f"✅ تم إنشاء التقرير '{report_title}' للـ DocType ({ref_doctype}) في موديول ({module}). "
            f"افتحه من قائمة التقارير عشان تظبط الأعمدة والفلاتر."
        )
        return {"reply": msg}

    except frappe.PermissionError:
        msg = (
            "You don't have permission to create this report."
            if lang == "English" else
            "ليس لديك صلاحية لإنشاء هذا التقرير."
        )
        return {"reply": msg}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "ERP AI Report Creation Error")
        msg = (
            "Sorry, something went wrong while creating the report. Please try again "
            "or contact your administrator."
            if lang == "English" else
            "عذراً، حدث خطأ أثناء إنشاء التقرير. برجاء المحاولة مرة أخرى أو التواصل مع مسؤول النظام."
        )
        return {"reply": msg}


@frappe.whitelist()
def ask(message, conversation=None, file_data=None, file_name=None):
    if conversation:
        try:
            conversation = json.loads(conversation)
        except Exception:
            conversation = []
    else:
        conversation = []

    full_message = message or ""
    if file_data:
        full_message = f"[Attached File: {file_name}]\nFile Content:\n{file_data}\n\nUser Question:\n{full_message}"
        # A file attachment is almost always a question about the file's
        # content, not a request to create a system Report — skip straight
        # to a normal chat reply.
        return call_ai_service(full_message, conversation)

    lang = _detect_lang(full_message)

    # 1) Is this message answering a pending report-creation confirmation
    #    from the previous turn?
    pending = _extract_pending_confirmation(conversation)
    if pending:
        if _is_affirmative(full_message):
            return _create_report_now(pending, lang)
        if _is_negative(full_message):
            msg = (
                "No problem, I won't create that report."
                if lang == "English" else
                "تمام، مش هعمل التقرير ده."
            )
            return {"reply": msg}
        # Ambiguous reply to a pending confirmation — don't guess; treat it
        # as a fresh message instead of silently creating or discarding.

    # 2) Otherwise, only pay for intent classification if the message
    #    plausibly mentions a report at all.
    lower_message = full_message.lower()
    looks_like_report_request = any(kw in lower_message for kw in REPORT_TRIGGER_KEYWORDS)

    if looks_like_report_request:
        intent = _classify_intent(full_message)
        if intent.get("action") == "create_report":
            return _propose_report_creation(intent, full_message, conversation, lang)

    return call_ai_service(full_message, conversation)


def call_ai_service(message, conversation):
    lang = _detect_lang(message)
    reply = ""

    try:
        # Import kept inside the try block (moved from module scope) so that
        # if erp_ai.ai.service fails to import or doesn't expose the
        # expected name, the user gets the normal graceful fallback message
        # below instead of an unhandled 500 error from the whitelisted
        # endpoint.
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
        frappe.log_error("AI generator returned an empty reply.", "ERP AI Empty Reply")
        reply = EMPTY_REPLY_MESSAGE[lang]

    return {"reply": reply}


@frappe.whitelist()
def export_data_to_csv(data_json, filename="erp_report.csv"):
    """
    دالة تصدير البيانات إلى ملف CSV للعميل مباشرة من الشات
    """
    try:
        if isinstance(data_json, str):
            data = frappe.parse_json(data_json)
        else:
            data = data_json

        if not data or not isinstance(data, list):
            frappe.throw("البيانات المرسلة غير صالحة للتصدير.")

        output = io.StringIO()
        if isinstance(data[0], dict):
            fieldnames = data[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        else:
            writer = csv.writer(output)
            for row in data:
                if isinstance(row, (list, tuple)):
                    writer.writerow(row)
                else:
                    writer.writerow([row])

        csv_content = output.getvalue()
        output.close()

        return {
            "status": "success",
            "file_name": filename,
            "filedata": csv_content
        }
    except Exception:
        frappe.log_error(frappe.get_traceback(), "CSV Export Error")
        return {"status": "error", "message": "حدث خطأ أثناء تصدير الملف. برجاء المحاولة مرة أخرى."}