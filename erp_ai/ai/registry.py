import json
import frappe

TOOLS = {}

def register_tool(name, description, parameters, func):
    TOOLS[name] = {
        "name": name,
        "description": description,
        "parameters": parameters or {},
        "function": func,
    }

def get_tools():
    return TOOLS

def list_tools():
    return list(TOOLS.values())

def get_functions():
    functions_list = []
    for tool in TOOLS.values():
        param_properties = {}
        required_fields = []
        
        if tool.get("parameters"):
            for param_name, param_meta in tool["parameters"].items():
                param_properties[param_name] = {
                    "type": param_meta.get("type", "string").upper(),
                    "description": param_meta.get("description", "")
                }
                if param_meta.get("type") == "array":
                    param_properties[param_name]["items"] = {"type": "STRING"}
                
                if param_meta.get("required"):
                    required_fields.append(param_name)

        functions_list.append({
            "name": tool["name"],
            "description": tool["description"],
            "parameters": {
                "type": "OBJECT",
                "properties": param_properties,
                "required": required_fields if required_fields else None
            }
        })
    return functions_list

def get_tool(name):
    return TOOLS.get(name)


def run_erp_query(doctype, fields=None, filters=None, limit=20, **kwargs):
    """
    دالة ذكية وآمنة لجلب البيانات والعدد الإجمالي من أي DocType مع تحسينات الأداء
    """
    try:
        order_by = kwargs.get("order_by") or kwargs.get("orderby") or "creation desc"

        if isinstance(fields, str):
            try:
                fields = json.loads(fields)
            except:
                fields = [f.strip() for f in fields.split(",")]
            
        if isinstance(filters, str):
            try:
                filters = json.loads(filters)
            except:
                filters = {}

        limit = min(int(limit or 20), 100)

        if not fields or fields == ["name"]:
            fields = ["name", "customer", "grand_total", "posting_date"] if doctype == "Sales Invoice" else ["*"]

        total_count = frappe.db.count(doctype, filters=filters)

        data = frappe.get_list(
            doctype,
            fields=fields,
            filters=filters,
            order_by=order_by,
            limit_page_length=limit
        )

        return {
            "total_count": total_count,
            "data": data
        }
    except Exception as e:
        frappe.log_error(title="ERP AI Query Error", message=str(e))
        return {"error": str(e)}


def universal_fallback_search(doctype=None, txt=None, filters=None, limit=10):
    """
    Universal Fallback Tool: أداة احتياطية شاملة لجلب أي بيانات من أي Doctype عند الحاجة.
    """
    try:
        if not doctype:
            doctype = "ToDo"
            
        if isinstance(filters, str):
            filters = frappe.parse_json(filters)
        
        if not filters:
            filters = {}

        limit = min(int(limit or 10), 50)

        if txt and not filters:
            meta = frappe.get_meta(doctype)
            search_field = meta.get_search_fields()[0] if meta.get_search_fields() else "name"
            filters[search_field] = ["like", f"%{txt}%"]

        data = frappe.get_all(
            doctype,
            filters=filters,
            fields=["*"],
            limit_page_length=limit,
            order_by="modified desc"
        )

        return {
            "status": "success",
            "doctype": doctype,
            "total_count": len(data),
            "data": data
        }

    except Exception as e:
        frappe.log_error(message=str(e), title="Universal Fallback Tool Error")
        return {
            "status": "error",
            "message": str(e),
            "data": []
        }


def manage_erp_document(doctype, docname, action, data=None):
    try:
        action = action.lower().strip()
        perm_type_map = {
            "cancel": "cancel",
            "submit": "submit",
            "update": "write",
            "delete": "delete"
        }
        required_perm = perm_type_map.get(action, "write")
        
        if not frappe.has_permission(doctype, required_perm, docname):
            return {"status": "error", "message": f"عذراً، لا تملك صلاحية ({action}) على هذا المستند ({docname})."}
        
        doc = frappe.get_doc(doctype, docname)
        
        if action == "cancel":
            if doc.docstatus == 1:
                doc.cancel()
                return {"status": "success", "message": f"تم إلغاء المستند ({docname}) بنجاح تام."}
            return {"status": "error", "message": f"المستند ({docname}) ليس في حالة معتمدة لكي يتم إلغاؤه."}
            
        elif action == "submit":
            if doc.docstatus == 0:
                doc.submit()
                return {"status": "success", "message": f"تم اعتماد المستند ({docname}) بنجاح تام."}
            return {"status": "error", "message": f"المستند ({docname}) معتمد مسبقاً أو ملغي."}
            
        elif action == "update":
            if doc.docstatus != 0:
                return {"status": "error", "message": f"لا يمكن تعديل مستند معتمد أو ملغي ({docname}) إلا بعد إلغائه أولاً."}
            
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except:
                    pass
            
            if isinstance(data, dict):
                doc.update(data)
                doc.save()
                return {"status": "success", "message": f"تم تحديث المستند ({docname}) بنجاح."}
            else:
                return {"status": "error", "message": "البيانات المراد تحديثها غير صالحة."}
                
        elif action == "delete":
            if doc.docstatus == 0:
                frapp_doc = frappe.get_doc(doctype, docname)
                frapp_doc.delete()
                return {"status": "success", "message": f"تم حذف المستند ({docname}) بنجاح."}
            return {"status": "error", "message": "لا يمكن حذف مستند معتمد أو ملغي، يجب إلغاؤه أولاً."}
            
        else:
            return {"status": "error", "message": f"الإجراء غير معروف: {action}"}
            
    except Exception as e:
        frappe.log_error(title=f"ERP AI Document Action Error [{action}]", message=frappe.get_traceback())
        return {"status": "error", "message": str(e)}


def create_erp_report(report_title, report_type="Report Builder", ref_doctype=None, module="Accounts", query_text=None):
    """
    أداة مخصصة لإنشاء وحفظ التقارير في نظام ERPNext
    """
    try:
        if not frappe.has_permission("Report", "create"):
            return {"status": "error", "message": "ليس لديك صلاحية إنشاء تقارير في النظام."}

        if frappe.db.exists("Report", {"report_name": report_title}):
            return {"status": "error", "message": f"التقرير '{report_title}' موجود مسبقاً."}

        report_doc = {
            "doctype": "Report",
            "report_name": report_title,
            "report_type": report_type,
            "is_standard": "No",
            "module": module,
        }

        if report_type == "Report Builder":
            if not ref_doctype:
                return {"status": "error", "message": "يجب تحديد نوع المستند (DocType) الأساسي للتقرير."}
            report_doc["ref_doctype"] = ref_doctype
        elif report_type == "Query Report":
            if not query_text:
                return {"status": "error", "message": "يجب توفير استعلام SQL لإنشاء التقرير."}
            report_doc["query"] = query_text
        elif report_type == "Script Report":
            if ref_doctype:
                report_doc["dependencies"] = ref_doctype

        doc = frappe.get_doc(report_doc)
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "message": f"تم إنشاء التقرير ({report_type}) تحت اسم '{report_title}' بنجاح تام.",
            "report_name": doc.name
        }
    except Exception as e:
        frappe.log_error(title="ERP AI Report Creation Error", message=str(e))
        return {"status": "error", "message": str(e)}


def create_erp_dashboard(dashboard_name, module="Accounts"):
    """
    أداة مخصصة لإنشاء وحفظ لوحات التحكم مع إنشاء Chart افتراضي لمنع خطأ الجدول الإجباري
    """
    try:
        if not frappe.has_permission("Dashboard", "create"):
            return {"status": "error", "message": "ليس لديك صلاحية إنشاء لوحات تحكم."}

        if frappe.db.exists("Dashboard", dashboard_name):
            return {"status": "error", "message": f"لوحة التحكم '{dashboard_name}' موجودة بالفعل."}

        # إنشاء Dashboard Chart افتراضي لتجاوز خطأ إلزاميّة جدول الـ Charts
        chart_name = f"{dashboard_name} Chart"
        if not frappe.db.exists("Dashboard Chart", chart_name):
            try:
                chart_doc = frappe.get_doc({
                    "doctype": "Dashboard Chart",
                    "chart_name": chart_name,
                    "chart_type": "Count",
                    "document_type": "ToDo",
                    "interval": "Monthly",
                    "timeseries": 1,
                    "module": module
                })
                chart_doc.insert(ignore_permissions=True)
            except Exception:
                pass

        # تجهيز المستند مع ربط الـ Chart الإجباري
        doc_data = {
            "doctype": "Dashboard",
            "dashboard_name": dashboard_name,
            "module": module,
            "is_default": 0
        }
        
        if frappe.db.exists("Dashboard Chart", chart_name):
            doc_data["charts"] = [{"chart": chart_name}]

        doc = frappe.get_doc(doc_data)
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "message": f"تم إنشاء لوحة التحكم '{dashboard_name}' بنجاح في موديول {module}.",
            "dashboard_name": doc.name
        }
    except Exception as e:
        frappe.log_error(title="ERP AI Dashboard Creation Error", message=str(e))
        return {"status": "error", "message": str(e)}


# تسجيل الأدوات
register_tool(
    name="run_erp_query",
    description=(
        "Use this tool to fetch records, data, analytics, and lists from any ERPNext DocType. "
        "CRITICAL INSTRUCTION FOR ANALYTICS/SUMMARIES: If the user asks for 'top selling products', "
        "'best customers', 'total sales', or any analytical question, DO NOT just fetch raw records or give up. "
        "You MUST fetch the relevant transaction child tables (e.g., 'Sales Invoice Item' for items) "
        "with appropriate fields (like item_code, qty, amount) so you can process and present the exact answer."
    ),
    parameters={
        "doctype": {"type": "string", "description": "The exact Frappe DocType name", "required": True},
        "fields": {"type": "string", "description": "A JSON array of fields or comma-separated strings to fetch", "required": False},
        "filters": {"type": "string", "description": "A JSON string representing filters to apply", "required": False},
        "order_by": {"type": "string", "description": "Field to sort by", "required": False},
        "limit": {"type": "integer", "description": "Max number of records to fetch", "required": False}
    },
    func=run_erp_query
)

register_tool(
    name="universal_fallback_search",
    description="Universal fallback tool to search and retrieve data or records from any DocType when specific queries fail.",
    parameters={
        "doctype": {"type": "string", "description": "DocType to search", "required": False},
        "txt": {"type": "string", "description": "Search keyword", "required": False},
        "filters": {"type": "string", "description": "JSON filters string", "required": False},
        "limit": {"type": "integer", "description": "Max limit", "required": False}
    },
    func=universal_fallback_search
)

register_tool(
    name="manage_erp_document",
    description="Manage lifecycle actions (submit, cancel, update, delete) on any ERPNext document.",
    parameters={
        "doctype": {"type": "string", "description": "DocType name", "required": True},
        "docname": {"type": "string", "description": "Name of the document", "required": True},
        "action": {"type": "string", "description": "Action to perform: submit, cancel, update, delete", "required": True},
        "data": {"type": "string", "description": "JSON data for update action", "required": False}
    },
    func=manage_erp_document
)

register_tool(
    name="create_erp_report",
    description="Create and save a Report (Report Builder, Query Report, or Script Report) in ERPNext.",
    parameters={
        "report_title": {"type": "string", "description": "Title of the report", "required": True},
        "report_type": {"type": "string", "description": "Report Builder, Query Report, or Script Report", "required": False},
        "ref_doctype": {"type": "string", "description": "Target DocType for Report Builder", "required": False},
        "module": {"type": "string", "description": "ERPNext Module", "required": False},
        "query_text": {"type": "string", "description": "SQL query for Query Report", "required": False}
    },
    func=create_erp_report
)

register_tool(
    name="create_erp_dashboard",
    description="Create and save a new Dashboard in ERPNext.",
    parameters={
        "dashboard_name": {"type": "string", "description": "Name of the dashboard", "required": True},
        "module": {"type": "string", "description": "ERPNext Module", "required": False}
    },
    func=create_erp_dashboard
)