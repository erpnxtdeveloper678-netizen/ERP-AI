"""
HR tools (ERPNext's HR module: Employee, Leave Allocation, Leave
Application, Attendance).

Every tool here is registered with providers=["claude"] (see decorators.py /
registry.py) - none of them are exposed to the Gemini provider.

Follows the exact same security model as tools/documents.py: the AI model is
an untrusted caller acting as frappe.session.user, every doctype/fieldname is
validated with the shared helpers in tools/_security.py, and every action
goes through frappe's normal has_permission() checks - nothing here uses
ignore_permissions or raw SQL.
"""

import frappe
from erp_ai.ai.decorators import ai_tool
from erp_ai.ai.tools._security import validate_doctype, check_permission, get_writable_fieldnames, resolve_document_name
from erp_ai.ai.tools.analytics import analyze_data


@ai_tool(
    name="get_leave_balance",
    description=(
        "Get an employee's leave balance: total allocated minus approved "
        "leave taken, optionally for one leave_type only (otherwise broken "
        "down per leave_type they have an allocation for)."
    ),
    parameters={
        "employee": {"type": "string", "required": True},
        "leave_type": {"type": "string", "description": "Optional. Restrict to one leave type."},
    },
    providers=["claude"],
)
def get_leave_balance(employee, leave_type=None, **kwargs):
    validate_doctype("Employee")
    employee = resolve_document_name("Employee", employee, "employee_name")
    check_permission("Employee", "read", doc=employee)
    validate_doctype("Leave Allocation")
    check_permission("Leave Allocation", "read")

    alloc_filters = {"employee": employee, "docstatus": 1}
    if leave_type:
        alloc_filters["leave_type"] = leave_type

    allocations = frappe.get_list(
        "Leave Allocation",
        filters=alloc_filters,
        fields=["leave_type", "new_leaves_allocated", "from_date", "to_date"],
        limit_page_length=100,
    )

    result = []
    for alloc in allocations:
        taken_filters = {
            "employee": employee, "leave_type": alloc.leave_type,
            "status": "Approved", "docstatus": 1,
            "from_date": [">=", alloc.from_date],
            "to_date": ["<=", alloc.to_date],
        }
        taken = analyze_data("Leave Application", "sum", field="total_leave_days", filters=taken_filters)
        taken_days = taken.get("value", 0) or 0
        result.append({
            "leave_type": alloc.leave_type,
            "allocated": alloc.new_leaves_allocated,
            "taken": taken_days,
            "balance": float(alloc.new_leaves_allocated or 0) - float(taken_days or 0),
            "period": f"{alloc.from_date} to {alloc.to_date}",
        })

    return {"employee": employee, "leave_type": leave_type, "balances": result}


@ai_tool(
    name="apply_leave",
    description=(
        "Submit a leave application for an employee. Inserted as a DRAFT - "
        "not automatically submitted/approved; use submit_document (if the "
        "current user's role can self-approve) or apply_workflow_action once "
        "the request is confirmed."
    ),
    parameters={
        "employee": {"type": "string", "required": True},
        "leave_type": {"type": "string", "required": True},
        "from_date": {"type": "string", "required": True, "description": "YYYY-MM-DD"},
        "to_date": {"type": "string", "required": True, "description": "YYYY-MM-DD"},
        "reason": {"type": "string"},
        "half_day": {"type": "boolean", "description": "Default false."},
    },
    providers=["claude"],
)
def apply_leave(employee, leave_type, from_date, to_date, reason=None, half_day=False, **kwargs):
    validate_doctype("Employee")
    employee = resolve_document_name("Employee", employee, "employee_name")
    check_permission("Employee", "read", doc=employee)
    validate_doctype("Leave Application")
    check_permission("Leave Application", "create")

    if not frappe.db.exists("Leave Type", leave_type):
        frappe.throw(f"Unknown Leave Type: '{leave_type}'.")

    allowed = get_writable_fieldnames("Leave Application")
    data = {
        "employee": employee, "leave_type": leave_type,
        "from_date": from_date, "to_date": to_date,
        "description": reason, "half_day": 1 if half_day else 0,
    }
    clean_data = {k: v for k, v in data.items() if k in allowed and v is not None}

    doc = frappe.new_doc("Leave Application")
    doc.update(clean_data)
    doc.insert()
    return {"status": "success", "doctype": "Leave Application", "name": doc.name, "employee": employee}


@ai_tool(
    name="get_attendance_summary",
    description=(
        "Count of Attendance records by status (Present/Absent/On Leave/"
        "Half Day/...) for one employee over a date range."
    ),
    parameters={
        "employee": {"type": "string", "required": True},
        "from_date": {"type": "string", "required": True, "description": "YYYY-MM-DD"},
        "to_date": {"type": "string", "required": True, "description": "YYYY-MM-DD"},
    },
    providers=["claude"],
)
def get_attendance_summary(employee, from_date, to_date, **kwargs):
    validate_doctype("Employee")
    employee = resolve_document_name("Employee", employee, "employee_name")
    check_permission("Employee", "read", doc=employee)
    validate_doctype("Attendance")
    check_permission("Attendance", "read")

    filters = {
        "employee": employee, "docstatus": 1,
        "attendance_date": ["between", [from_date, to_date]],
    }
    breakdown = analyze_data("Attendance", "group", group_by="status", aggregate="count", filters=filters, limit=20)

    return {
        "employee": employee, "from_date": from_date, "to_date": to_date,
        "by_status": {row["group_field"]: row["value"] for row in breakdown.get("data", [])},
    }
    