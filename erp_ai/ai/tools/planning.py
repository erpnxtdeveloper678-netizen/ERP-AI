"""
Multi-step planning tools - for requests that are really several related
steps (e.g. "onboard this new customer: create them, set payment terms,
create their first sales order, and assign someone to follow up").

Deliberately built on the standard Project/Task doctypes instead of
inventing a new bespoke "Plan" DocType: it needs no migration/fixture to
install, every step is a real Task the user can see and edit in the normal
ERPNext UI (not something only visible inside the chat), and progress
tracking is free - get_project_summary (tools/projects.py) already reports
on any project's tasks.

Every tool here is registered with providers=["claude"]. Same security
model as the rest of tools/.
"""

import json
import frappe
from erp_ai.ai.decorators import ai_tool
from erp_ai.ai.tools._security import validate_doctype, check_permission


@ai_tool(
    name="create_plan",
    description=(
        "Break a multi-step request into a tracked plan: creates one Task per "
        "step (optionally grouped under a new or existing Project). Use this "
        "instead of silently doing several unrelated actions in a row whenever "
        "the user's request has 3+ distinct steps they'd want to see and track - "
        "it makes the plan visible and editable in the ERPNext UI, not just "
        "mentioned in the chat reply. Check progress later with get_project_summary "
        "(tools/projects.py) using the returned project name."
    ),
    parameters={
        "title": {"type": "string", "required": True, "description": "Short name for the plan - used as the Project name if a new one is created."},
        "steps": {
            "type": "array", "required": True,
            "description": "List of step descriptions (strings), or {subject, assigned_to?, due_date?} objects for more control.",
        },
        "project": {"type": "string", "description": "Optional. Group the steps under an EXISTING project instead of creating a new one."},
    },
    providers=["claude"],
)
def create_plan(title, steps, project=None, **kwargs):
    if isinstance(steps, str):
        try:
            steps = json.loads(steps)
        except Exception:
            frappe.throw("`steps` must be a list of step descriptions or {subject, ...} objects.")
    if not isinstance(steps, list) or not steps:
        frappe.throw("`steps` must be a non-empty list.")

    validate_doctype("Task")
    check_permission("Task", "create")

    if project:
        validate_doctype("Project")
        if not frappe.db.exists("Project", project):
            frappe.throw(f"Unknown Project: '{project}'.")
        check_permission("Project", "read", doc=project)
        project_name = project
        created_project = False
    else:
        validate_doctype("Project")
        check_permission("Project", "create")
        proj = frappe.new_doc("Project")
        proj.project_name = title
        proj.insert()
        project_name = proj.name
        created_project = True

    created_tasks = []
    for i, step in enumerate(steps, start=1):
        if isinstance(step, str):
            step = {"subject": step}
        if not isinstance(step, dict) or not step.get("subject"):
            frappe.throw(f"Step {i} needs at least a `subject`.")

        task = frappe.new_doc("Task")
        task.subject = step["subject"]
        task.project = project_name
        task.task_weight = i  # keeps the steps in their given order on the Task list
        if step.get("due_date"):
            task.exp_end_date = step["due_date"]
        task.insert()

        if step.get("assigned_to"):
            from frappe.desk.form.assign_to import add as assign_to_add
            assign_to_add({
                "assign_to": [step["assigned_to"]],
                "doctype": "Task",
                "name": task.name,
                "description": f"Step {i} of plan '{title}': {step['subject']}",
            })

        created_tasks.append({"name": task.name, "subject": task.subject, "assigned_to": step.get("assigned_to")})

    return {
        "status": "success",
        "plan_title": title,
        "project": project_name,
        "project_created": created_project,
        "steps_created": created_tasks,
    }
    