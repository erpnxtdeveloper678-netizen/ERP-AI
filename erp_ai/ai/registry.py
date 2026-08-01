import json
import frappe
from frappe import _

# ---------------------------------------------------------
# Tool Registry & Metadata System
# ---------------------------------------------------------

_REGISTRY = {}


def register_tool(name, description, parameters):
    """
    Decorator to register a function and define its JSON schema to pass to the LLM.
    """
    def decorator(func):
        _REGISTRY[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "function": func
        }
        return func
    return decorator


def get_tools():
    """Return the full dictionary of registered tools."""
    return _REGISTRY


def get_functions():
    """Return a list of tool definitions ready to pass to the AI Model."""
    return [
        {
            "name": data["name"],
            "description": data["description"],
            "parameters": data["parameters"]
        }
        for data in _REGISTRY.values()
    ]


# ---------------------------------------------------------
# 1. Schema & Field Discovery
# ---------------------------------------------------------
@register_tool(
    name="get_doctype_schema",
    description="Inspect ERPNext DocType metadata to discover available fields and mandatory attributes.",
    parameters={
        "type": "object",
        "properties": {
            "doctype": {"type": "string", "description": "Target ERPNext DocType (e.g., Sales Order, Customer)"}
        },
        "required": ["doctype"]
    }
)
def get_doctype_schema(doctype):
    try:
        if not frappe.db.exists("DocType", doctype):
            return {"status": "error", "message": f"DocType '{doctype}' does not exist."}

        meta = frappe.get_meta(doctype)
        fields = []
        for f in meta.fields:
            if not f.is_virtual and f.fieldtype not in ["Section Break", "Column Break", "Tab Break"]:
                fields.append({
                    "fieldname": f.fieldname,
                    "label": f.label,
                    "fieldtype": f.fieldtype,
                    "reqd": f.reqd,
                    "options": f.options
                })

        return {
            "status": "success",
            "doctype": doctype,
            "title_field": meta.title_field or "name",
            "search_fields": meta.search_fields,
            "fields": fields
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------
# 2. Universal Data Fetching & Querying
# ---------------------------------------------------------
@register_tool(
    name="run_erp_query",
    description="Query ERPNext records with flexible filters, field selection, ordering, and optional child table inclusion.",
    parameters={
        "type": "object",
        "properties": {
            "doctype": {"type": "string", "description": "Target DocType"},
            "filters": {"type": "object", "description": "Dict or JSON object of filter conditions"},
            "fields": {"type": "array", "items": {"type": "string"}, "description": "List of field names to select"},
            "order_by": {"type": "string", "description": "Sorting string (e.g., 'creation desc')"},
            "limit": {"type": "integer", "description": "Number of records to return (default 20)"},
            "include_child_table": {"type": "string", "description": "Optional child table fieldname to populate"}
        },
        "required": ["doctype"]
    }
)
def run_erp_query(doctype, filters=None, fields=None, order_by=None, limit=20, include_child_table=None):
    try:
        if isinstance(filters, str):
            try: filters = json.loads(filters)
            except Exception: filters = {}

        if isinstance(fields, str):
            try: fields = json.loads(fields)
            except Exception: fields = None

        if not fields:
            fields = ["*"]

        records = frappe.get_list(
            doctype,
            filters=filters or {},
            fields=fields,
            order_by=order_by or "modified desc",
            limit_page_length=limit or 20
        )

        if include_child_table and records:
            for doc in records:
                if "name" in doc:
                    child_records = frappe.get_all(
                        include_child_table,
                        filters={"parent": doc["name"]},
                        fields=["*"]
                    )
                    doc[include_child_table] = child_records

        return {
            "status": "success",
            "count": len(records),
            "data": records
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------
# 3. Universal Fallback Search
# ---------------------------------------------------------
@register_tool(
    name="universal_fallback_search",
    description="Fuzzy search across standard title/name fields when specific filters fail.",
    parameters={
        "type": "object",
        "properties": {
            "doctype": {"type": "string"},
            "query": {"type": "string"},
            "limit": {"type": "integer"}
        },
        "required": ["doctype", "query"]
    }
)
def universal_fallback_search(doctype, query, limit=10):
    try:
        meta = frappe.get_meta(doctype)
        search_fields = [meta.title_field] if meta.title_field else []
        if "name" not in search_fields:
            search_fields.append("name")

        or_filters = [[doctype, f_name, "like", f"%{query}%"] for f_name in search_fields if f_name]

        results = frappe.get_all(
            doctype,
            or_filters=or_filters,
            fields=["*"],
            limit_page_length=limit or 10
        )
        return {"status": "success", "count": len(results), "data": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------
# 4. Create ERP Documents
# ---------------------------------------------------------
@register_tool(
    name="create_erp_document",
    description="Create a new ERPNext document.",
    parameters={
        "type": "object",
        "properties": {
            "doctype": {"type": "string"},
            "doc_data": {"type": "object", "description": "Key-value dictionary of document values"}
        },
        "required": ["doctype", "doc_data"]
    }
)
def create_erp_document(doctype, doc_data):
    try:
        if isinstance(doc_data, str):
            doc_data = json.loads(doc_data)

        doc = frappe.new_doc(doctype)
        doc.update(doc_data)
        doc.insert(ignore_permissions=False)
        frappe.db.commit()

        return {
            "status": "success",
            "message": f"Document '{doc.name}' created successfully.",
            "name": doc.name,
            "doc": doc.as_dict()
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------
# 5. Manage ERP Documents (Submit, Cancel, Update, Delete)
# ---------------------------------------------------------
@register_tool(
    name="manage_erp_document",
    description="Perform document lifecycle actions: 'submit', 'cancel', 'update', or 'delete'.",
    parameters={
        "type": "object",
        "properties": {
            "doctype": {"type": "string"},
            "name": {"type": "string"},
            "action": {"type": "string", "enum": ["submit", "cancel", "update", "delete"]},
            "update_data": {"type": "object", "description": "Data dict if action is 'update'"}
        },
        "required": ["doctype", "name", "action"]
    }
)
def manage_erp_document(doctype, name, action, update_data=None):
    try:
        if not frappe.db.exists(doctype, name):
            return {"status": "error", "message": f"{doctype} '{name}' not found."}

        doc = frappe.get_doc(doctype, name)

        if action == "submit":
            doc.submit()
            msg = f"Document '{name}' submitted successfully."
        elif action == "cancel":
            doc.cancel()
            msg = f"Document '{name}' cancelled successfully."
        elif action == "delete":
            frappe.delete_doc(doctype, name)
            msg = f"Document '{name}' deleted successfully."
        elif action == "update":
            if isinstance(update_data, str):
                update_data = json.loads(update_data)
            if update_data:
                doc.update(update_data)
                doc.save()
                msg = f"Document '{name}' updated successfully."
            else:
                return {"status": "error", "message": "No update_data provided."}
        else:
            return {"status": "error", "message": f"Unknown action '{action}'."}

        frappe.db.commit()
        return {"status": "success", "message": msg, "doc": doc.as_dict() if action != "delete" else None}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------
# 6. Execute Doc Method
# ---------------------------------------------------------
@register_tool(
    name="execute_doc_method",
    description="Invoke specific Python methods attached to a document instance.",
    parameters={
        "type": "object",
        "properties": {
            "doctype": {"type": "string"},
            "name": {"type": "string"},
            "method": {"type": "string"},
            "args": {"type": "object"}
        },
        "required": ["doctype", "name", "method"]
    }
)
def execute_doc_method(doctype, name, method, args=None):
    try:
        doc = frappe.get_doc(doctype, name)
        if not hasattr(doc, method):
            return {"status": "error", "message": f"Method '{method}' does not exist on {doctype}."}

        if isinstance(args, str):
            args = json.loads(args)

        method_fn = getattr(doc, method)
        result = method_fn(**(args or {}))
        frappe.db.commit()

        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------
# 7. System Analytics & Aggregations
# ---------------------------------------------------------
@register_tool(
    name="get_system_analytics",
    description="Perform high-level SQL aggregations (COUNT, SUM, AVG) directly.",
    parameters={
        "type": "object",
        "properties": {
            "doctype": {"type": "string"},
            "function": {"type": "string", "enum": ["COUNT", "SUM", "AVG", "MIN", "MAX"]},
            "field": {"type": "string"},
            "group_by": {"type": "string"},
            "filters": {"type": "object"}
        },
        "required": ["doctype", "function"]
    }
)
def get_system_analytics(doctype, function, field="name", group_by=None, filters=None):
    try:
        if isinstance(filters, str):
            try: filters = json.loads(filters)
            except Exception: filters = {}

        field_to_aggregate = field if field else "name"
        expr = f"{function}({field_to_aggregate})"

        fields = [f"{expr} as value"]
        if group_by:
            fields.append(group_by)

        data = frappe.get_all(
            doctype,
            filters=filters or {},
            fields=fields,
            group_by=group_by,
            order_by="value desc"
        )
        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------
# 8. Create Custom Reports
# ---------------------------------------------------------
@register_tool(
    name="create_erp_report",
    description="Create saved Builder or Query Reports in ERPNext.",
    parameters={
        "type": "object",
        "properties": {
            "report_name": {"type": "string"},
            "ref_doctype": {"type": "string"},
            "report_type": {"type": "string", "enum": ["Report Builder", "Query Report"]},
            "query": {"type": "string", "description": "Required if report_type is Query Report"}
        },
        "required": ["report_name", "ref_doctype", "report_type"]
    }
)
def create_erp_report(report_name, ref_doctype, report_type="Report Builder", query=None):
    try:
        if frappe.db.exists("Report", report_name):
            return {"status": "error", "message": f"Report '{report_name}' already exists."}

        rep = frappe.new_doc("Report")
        rep.report_name = report_name
        rep.ref_doctype = ref_doctype
        rep.report_type = report_type
        rep.is_standard = "No"

        if report_type == "Query Report":
            if not query:
                return {"status": "error", "message": "SQL Query is required for Query Report."}
            rep.query = query

        rep.insert(ignore_permissions=True)
        frappe.db.commit()

        return {"status": "success", "message": f"Report '{report_name}' created successfully."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------
# 9. Create ERP Dynamic Dashboards (Fully Dynamic with Safe Fallbacks)
# ---------------------------------------------------------
@register_tool(
    name="create_erp_dashboard",
    description="Create a fully custom ERPNext Dashboard based on dynamic charts and cards passed by the LLM. Execute immediately without confirmation.",
    parameters={
        "type": "object",
        "properties": {
            "dashboard_name": {"type": "string", "description": "Title of the dashboard"},
            "module": {"type": "string", "description": "ERPNext Module (Selling, Stock, Accounts, etc.)"},
            "target_doctype": {"type": "string", "description": "DocType to gather data from (Sales Invoice, Purchase Order, etc.)"},
            "cards_config": {
                "type": "array",
                "description": "Dynamic list of Number Cards generated by AI based on user prompt",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "function": {"type": "string", "enum": ["Count", "Sum", "Average", "Minimum", "Maximum"]},
                        "field": {"type": "string"}
                    },
                    "required": ["label", "function"]
                }
            },
            "charts_config": {
                "type": "array",
                "description": "Dynamic list of Dashboard Charts generated by AI based on user prompt",
                "items": {
                    "type": "object",
                    "properties": {
                        "chart_name": {"type": "string"},
                        "type": {"type": "string", "enum": ["Bar", "Line", "Pie", "Donut", "Percentage"]},
                        "chart_type": {"type": "string", "enum": ["Group By", "Sum", "Count", "Average"]},
                        "group_by_field": {"type": "string"},
                        "aggregate_function": {"type": "string", "enum": ["Sum", "Count"]},
                        "aggregate_based_on": {"type": "string"},
                        "number_of_groups": {"type": "integer"}
                    },
                    "required": ["chart_name", "type", "chart_type", "group_by_field"]
                }
            }
        },
        "required": ["dashboard_name", "target_doctype"]
    }
)
def create_erp_dashboard(dashboard_name, module="Selling", target_doctype="Sales Invoice", charts_config=None, cards_config=None):
    try:
        if not frappe.has_permission("Dashboard", "create"):
            return {"status": "error", "message": "Permission denied: Cannot create Dashboards."}

        # Clear existing dashboard with the same name if exists
        if frappe.db.exists("Dashboard", dashboard_name):
            frappe.delete_doc("Dashboard", dashboard_name, ignore_permissions=True)

        if isinstance(charts_config, str):
            try: charts_config = json.loads(charts_config)
            except Exception: charts_config = []

        if isinstance(cards_config, str):
            try: cards_config = json.loads(cards_config)
            except Exception: cards_config = []

        cards_config = cards_config or []
        charts_config = charts_config or []

        meta = frappe.get_meta(target_doctype)
        field_names = [f.fieldname for f in meta.fields]

        default_date_field = "creation"
        for candidate in ["posting_date", "transaction_date", "date"]:
            if candidate in field_names:
                default_date_field = candidate
                break

        fallback_num_field = "grand_total" if "grand_total" in field_names else ("amount" if "amount" in field_names else None)
        fallback_group_field = "customer_name" if "customer_name" in field_names else ("status" if "status" in field_names else "name")

        # 🛡️ Safe Fallbacks: Automatically generate default cards & charts if LLM payload is empty
        if not cards_config:
            cards_config = [
                {"label": f"Total {target_doctype}s", "function": "Count"},
            ]
            if fallback_num_field:
                cards_config.append({"label": "Total Value", "function": "Sum", "field": fallback_num_field})

        if not charts_config:
            charts_config = [
                {
                    "chart_name": f"{target_doctype} Distribution",
                    "type": "Bar",
                    "chart_type": "Group By",
                    "group_by_field": fallback_group_field,
                    "aggregate_function": "Sum" if fallback_num_field else "Count",
                    "aggregate_based_on": fallback_num_field,
                    "number_of_groups": 5
                }
            ]

        card_names = []
        chart_names = []

        # ---------------------------------------------------------
        # 1️⃣ Build Number Cards Dynamically
        # ---------------------------------------------------------
        for idx, card in enumerate(cards_config):
            card_label = card.get("label", f"Card {idx+1}")
            c_name = f"{dashboard_name}-Card-{idx+1}"

            if frappe.db.exists("Number Card", c_name):
                frappe.delete_doc("Number Card", c_name, ignore_permissions=True)

            try:
                c_doc = frappe.new_doc("Number Card")
                c_doc.name = c_name
                c_doc.label = card_label
                c_doc.document_type = target_doctype
                c_doc.function = card.get("function", "Count")
                
                target_field = card.get("field")
                if c_doc.function in ["Sum", "Average", "Minimum", "Maximum"]:
                    if not target_field or target_field not in field_names:
                        target_field = fallback_num_field or "name"
                    c_doc.aggregate_function_based_on = target_field
                
                c_doc.module = module
                c_doc.is_standard = 0
                c_doc.insert(ignore_permissions=True)
                card_names.append(c_doc.name)
            except Exception as card_err:
                frappe.log_error(title="Number Card Creation Error", message=frappe.get_traceback())

        # ---------------------------------------------------------
        # 2️⃣ Build Dashboard Charts Dynamically
        # ---------------------------------------------------------
        VALID_CHART_TYPES = ["Count", "Sum", "Average", "Group By", "Custom", "Report"]
        VALID_VISUAL_TYPES = ["Line", "Bar", "Pie", "Percentage", "Donut", "Heatmap"]

        for idx, chart in enumerate(charts_config):
            ch_name = f"{dashboard_name}-Chart-{idx+1}"
            if frappe.db.exists("Dashboard Chart", ch_name):
                frappe.delete_doc("Dashboard Chart", ch_name, ignore_permissions=True)

            try:
                raw_type = str(chart.get("type") or "").strip()
                raw_chart_type = str(chart.get("chart_type") or "").strip()

                final_agg_type = raw_chart_type if raw_chart_type in VALID_CHART_TYPES else "Group By"
                final_visual_type = raw_type if raw_type in VALID_VISUAL_TYPES else "Bar"

                chart_doc = frappe.new_doc("Dashboard Chart")
                chart_doc.name = ch_name
                chart_doc.chart_name = chart.get("chart_name", f"Chart {idx+1}")
                chart_doc.document_type = target_doctype
                chart_doc.module = module
                chart_doc.is_standard = 0
                chart_doc.based_on = chart.get("based_on") or default_date_field

                chart_doc.chart_type = final_agg_type
                chart_doc.type = final_visual_type

                if chart_doc.chart_type == "Group By":
                    agg_fn = chart.get("aggregate_function", "Sum")
                    group_field = chart.get("group_by_field")
                    
                    if group_field == "customer" and "customer_name" in field_names:
                        group_field = "customer_name"

                    if not group_field or group_field not in field_names:
                        group_field = fallback_group_field

                    chart_doc.group_by_type = agg_fn
                    chart_doc.group_by_based_on = group_field
                    chart_doc.number_of_groups = chart.get("number_of_groups") or 5

                    if agg_fn == "Sum":
                        target_num_field = chart.get("aggregate_based_on")
                        if not target_num_field or target_num_field not in field_names:
                            target_num_field = fallback_num_field
                        chart_doc.aggregate_function_based_on = target_num_field
                    else:
                        chart_doc.aggregate_function_based_on = None

                chart_doc.filters_json = "[]"
                chart_doc.insert(ignore_permissions=True)
                chart_names.append(chart_doc.name)

            except Exception as chart_err:
                frappe.log_error(title="Dashboard Chart Creation Error", message=frappe.get_traceback())

        if not chart_names and not card_names:
            return {
                "status": "error",
                "message": "No valid chart or card configurations were provided to build the dashboard."
            }

        # ---------------------------------------------------------
        # 3️⃣ Save Dashboard Document
        # ---------------------------------------------------------
        dash_doc = frappe.new_doc("Dashboard")
        dash_doc.dashboard_name = dashboard_name
        dash_doc.module = module
        dash_doc.is_default = 0

        for c_id in card_names:
            dash_doc.append("cards", {"card": c_id})

        for ch_id in chart_names:
            dash_doc.append("charts", {"chart": ch_id})

        dash_doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "message": f"Successfully created dashboard '{dashboard_name}' with {len(card_names)} cards and {len(chart_names)} charts.",
            "dashboard_name": dash_doc.name
        }
    except Exception as e:
        frappe.log_error(title="ERP AI Dashboard Creation Error", message=frappe.get_traceback())
        return {"status": "error", "message": f"Failed to create dashboard: {str(e)}"}