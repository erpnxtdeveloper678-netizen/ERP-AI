"""
Single tool-execution entry point, used by both providers (claude.py and
gemini.py).

Permission enforcement happens *inside* each tool function (via
tools/_security.py's check_permission), not here - this layer's job is just
safe dispatch and turning exceptions into a clean {"error": ...} payload the
model can read and explain to the user, instead of a raw traceback.

Every call is also written to "AI Tool Log" (see _log_tool_call below) so an
admin can answer "who asked the assistant to touch what, and when".
"""

import json
import frappe
from erp_ai.ai.registry import get_tool

_REDACT_KEY_HINTS = ("password", "secret", "api_key", "apikey", "token")

_ARGS_LIMIT = 2000
_RESULT_LIMIT = 1000


def _safe_log(title, message):
    try:
        frappe.log_error(title=title, message=message)
    except Exception:
        pass


def _redact(value):
    if isinstance(value, dict):
        return {
            k: ("***" if any(hint in k.lower() for hint in _REDACT_KEY_HINTS) else _redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def _truncate(text: str, limit: int) -> str:
    if text and len(text) > limit:
        return text[:limit] + f"... [truncated, {len(text)} chars total]"
    return text or ""


def _log_tool_call(name, args, target_doctype, status, result):
    try:
        args_json = _truncate(json.dumps(_redact(args), ensure_ascii=False, default=str), _ARGS_LIMIT)
        result_text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)
        result_text = _truncate(result_text, _RESULT_LIMIT)

        frappe.get_doc({
            "doctype": "AI Tool Log",
            "user": frappe.session.user,
            "tool": name,
            "target_doctype": target_doctype or "",
            "status": status,
            "args": args_json,
            "result_summary": result_text,
        }).insert(ignore_permissions=True)
    except Exception:
        _safe_log("ERP AI Tool Log Error", frappe.get_traceback())


def execute_tool(name: str, args: dict = None):
    args = args or {}
    target_doctype = args.get("doctype") if isinstance(args, dict) else None

    tool = get_tool(name)
    if not tool or not tool.get("function"):
        error = {"error": f"Tool '{name}' is not registered."}
        _log_tool_call(name, args, target_doctype, "Error", error)
        return error

    try:
        clean_args = json.loads(json.dumps(args, default=str))
    except Exception:
        clean_args = args

    try:
        result = tool["function"](**clean_args)
        _log_tool_call(name, clean_args, target_doctype, "Success", result)
        return result
    except TypeError as e:
        _safe_log(
            f"ERP AI Executor Argument Error ({name})",
            f"{frappe.get_traceback()}\n\nArgs received: {clean_args}",
        )
        error = {"error": f"Invalid arguments for tool '{name}': {e}"}
        _log_tool_call(name, clean_args, target_doctype, "Error", error)
        return error
    except frappe.PermissionError as e:
        error = {"error": str(e) or f"Permission denied for tool '{name}'."}
        _log_tool_call(name, clean_args, target_doctype, "Error", error)
        return error
    except Exception as e:
        _safe_log(f"ERP AI Executor Error ({name})", frappe.get_traceback())
        error = {"error": str(e)}
        _log_tool_call(name, clean_args, target_doctype, "Error", error)
        return error
        