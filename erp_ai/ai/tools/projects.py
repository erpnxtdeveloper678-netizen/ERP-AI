"""
Projects & Tasks tools - ERPNext's Projects module (Project, Task).

Every tool here is registered with providers=["claude"]. Same security
model as the rest of tools/ - see tools/_security.py and the note at the
top of tools/inventory.py for the full rationale.
"""

import frappe
from erp_ai.ai.decorators import ai_tool
from erp_ai.ai.tools._security import validate_doctype, check_permission, resolve_document_name


@ai_tool(
    name="get_project_summary",
    description=(
        "Get an overview of one project: its status and percent complete, "
        "plus a breakdown of its tasks (open/overdue/completed counts and "
        "the overdue ones by name)."
    ),
    parameters={"project": {"type": "string", "required": True, "description": "Exact ID or project name/part of it - resolved automatically."}},
    providers=["claude"],
)
def get_project_summary(project, **kwargs):
    validate_doctype("Project")
    project = resolve_document_name("Project", project, "project_name")
    check_permission("Project", "read", doc=project)

    proj = frappe.get_doc("Project", project)
    info = {
        "name": proj.name,
        "project_name": getattr(proj, "project_name", None),
        "status": getattr(proj, "status", None),
        "percent_complete": getattr(proj, "percent_complete", None),
        "expected_start_date": getattr(proj, "expected_start_date", None),
        "expected_end_date": getattr(proj, "expected_end_date", None),
    }

    tasks = []
    if frappe.db.exists("DocType", "Task") and frappe.has_permission("Task", "read"):
        tasks = frappe.get_list(
            "Task",
            filters={"project": project},
            fields=["name", "subject", "status", "priority", "exp_end_date"],
            limit_page_length=200,
        )

    from frappe.utils import getdate, nowdate
    today = getdate(nowdate())
    counts = {"total": len(tasks), "open": 0, "completed": 0, "overdue": 0}
    overdue_tasks = []
    for t in tasks:
        status = (t.get("status") or "").lower()
        if status in ("completed", "cancelled"):
            counts["completed"] += 1
        else:
            counts["open"] += 1
            due = t.get("exp_end_date")
            if due and getdate(due) < today:
                counts["overdue"] += 1
                overdue_tasks.append({"name": t["name"], "subject": t["subject"], "due": str(due)})

    return {"project": info, "task_counts": counts, "overdue_tasks": overdue_tasks}


@ai_tool(
    name="create_task",
    description="Create a new Task, optionally under a Project and assigned to a user.",
    parameters={
        "subject": {"type": "string", "required": True},
        "project": {"type": "string", "description": "Optional. Exact ID or project name/part of it - resolved automatically."},
        "assigned_to": {"type": "string", "description": "Optional. User email to assign the task to."},
        "due_date": {"type": "string", "description": "Optional. YYYY-MM-DD."},
        "priority": {"type": "string", "description": "Optional. e.g. 'Low', 'Medium', 'High', 'Urgent'."},
        "description": {"type": "string", "description": "Optional."},
    },
    providers=["claude"],
)
def create_task(subject, project=None, assigned_to=None, due_date=None, priority=None, description=None, **kwargs):
    validate_doctype("Task")
    check_permission("Task", "create")

    doc = frappe.new_doc("Task")
    doc.subject = subject
    if project:
        validate_doctype("Project")
        project = resolve_document_name("Project", project, "project_name")
        check_permission("Project", "read", doc=project)
        doc.project = project
    if due_date:
        doc.exp_end_date = due_date
    if priority:
        doc.priority = priority
    if description:
        doc.description = description

    doc.insert()

    if assigned_to:
        from frappe.desk.form.assign_to import add as assign_to_add
        assign_to_add({
            "assign_to": [assigned_to],
            "doctype": "Task",
            "name": doc.name,
            "description": f"Assigned via ERP Assistant: {subject}",
        })

    return {"status": "success", "doctype": "Task", "name": doc.name, "project": project, "assigned_to": assigned_to}


@ai_tool(
    name="get_my_open_tasks",
    description="List Tasks assigned to the current user that are not yet completed - 'what's on my plate'.",
    parameters={"limit": {"type": "integer", "description": "Max rows, capped at 100. Default 50."}},
    providers=["claude"],
)
def get_my_open_tasks(limit=50, **kwargs):
    validate_doctype("Task")
    check_permission("Task", "read")

    limit = max(1, min(int(limit or 50), 100))
    user = frappe.session.user

    rows = frappe.get_list(
        "Task",
        filters=[
            ["_assign", "like", f"%{user}%"],
            ["status", "not in", ["Completed", "Cancelled"]],
        ],
        fields=["name", "subject", "project", "status", "priority", "exp_end_date"],
        order_by="exp_end_date asc",
        limit_page_length=limit,
    )
    return {"user": user, "open_tasks": rows}


@ai_tool(
    name="update_task_status",
    description="Change a Task's status (e.g. mark it 'Working', 'Completed', 'Cancelled').",
    parameters={
        "task": {"type": "string", "required": True},
        "status": {"type": "string", "required": True, "description": "e.g. 'Open', 'Working', 'Pending Review', 'Completed', 'Cancelled'."},
    },
    providers=["claude"],
)
def update_task_status(task, status, **kwargs):
    validate_doctype("Task")
    check_permission("Task", "write", doc=task)

    if not frappe.db.exists("Task", task):
        frappe.throw(f"Unknown Task: '{task}'.")

    doc = frappe.get_doc("Task", task)
    doc.status = status
    doc.save()

    return {"status": "success", "doctype": "Task", "name": doc.name, "new_status": doc.status}
    