import frappe

# القاموس المركزي لتخزين الأدوات المسجلة
TOOLS = {}

def register_tool(name, description, parameters, func):
    """
    Registers a tool in the central AI registry.
    """
    TOOLS[name] = {
        "name": name,
        "description": description,
        "parameters": parameters or {},
        "function": func,
    }

def get_tools():
    """
    Returns the raw TOOLS dictionary.
    """
    return TOOLS

def list_tools():
    """
    Returns a list of all registered tool metadata.
    """
    return list(TOOLS.values())

def get_functions():
    """
    Returns the tools formatted as raw dictionaries (JSON Schema)
    as required by the new Client SDK.
    """
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
    """
    Returns a specific tool by its name.
    """  
    return TOOLS.get(name)



def run_erp_query(doctype, fields=None, filters=None, limit=20, **kwargs):
    """
    دالة آمنة تتيح للـ AI جلب البيانات مباشرة من أي DocType في ERPNext
    """
    try:
        order_by = kwargs.get("order_by") or kwargs.get("orderby") or "creation desc"

        if isinstance(fields, str):
            import json
            try:
                fields = json.loads(fields)
            except:
                fields = [f.strip() for f in fields.split(",")]
            
        if isinstance(filters, str):
            import json
            try:
                filters = json.loads(filters)
            except:
                filters = {}

        if not fields or fields == ["name"]:
            fields = ["name", "customer", "grand_total", "posting_date"] if doctype == "Sales Invoice" else ["*"]

        data = frappe.get_list(
            doctype,
            fields=fields,
            filters=filters,
            order_by=order_by,
            limit_page_length=limit
        )
        return data
    except Exception as e:
        return {"error": str(e)}



def manage_erp_document(doctype, docname, action, data=None):
    """
    دالة موحدة وذكية لتنفيذ أي إجراء (action) على المستندات بناءً على صلاحيات المستخدم الفعلي:
    - cancel: إلغاء المستند
    - submit: اعتماد المستند
    - update: تحديث حقول معينة في المستند
    - delete: حذف المستند (إذا كان مسودة)
    """
    try:
        action = action.lower().strip()
        
        # 1. تحديد الصلاحية المطلوبة بناءً على نوع الإجراء
        perm_type_map = {
            "cancel": "cancel",
            "submit": "submit",
            "update": "write",
            "delete": "delete"
        }
        
        required_perm = perm_type_map.get(action, "write")
        
        # 2. التحقق من صلاحيات المستخدم الحالي على المستند
        if not frappe.has_permission(doctype, required_perm, docname):
            return {"status": "error", "message": f"عذراً، لا تملك صلاحية ({action}) على هذا المستند ({docname})."}
        
        doc = frappe.get_doc(doctype, docname)
        
        # 3. تنفيذ الإجراء المطلوب
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
                import json
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


register_tool(
    name="run_erp_query",
    description="Use this tool to fetch records, data, analytics, and lists from any ERPNext DocType like Sales Invoice, Customer, Item, Purchase Invoice, etc.",
    parameters={
        "doctype": {
            "type": "string",
            "description": "The exact Frappe DocType name (e.g., 'Sales Invoice', 'Customer')",
            "required": True
        },
        "fields": {
            "type": "string",
            "description": "A JSON array of fields or comma-separated strings to fetch",
            "required": False
        },
        "filters": {
            "type": "string",
            "description": "A JSON string representing filters to apply",
            "required": False
        },
        "order_by": {
            "type": "string",
            "description": "Field to sort by (e.g., 'grand_total desc')",
            "required": False
        },
        "limit": {
            "type": "integer",
            "description": "Max number of records to fetch (default 20)",
            "required": False
        }
    },
    func=run_erp_query
)

register_tool(
    name="manage_erp_document",
    description="Use this tool to perform full actions on documents in ERPNext such as canceling, submitting, updating, or deleting documents based on user permissions.",
    parameters={
        "doctype": {
            "type": "string",
            "description": "The exact Frappe DocType name (e.g., 'Sales Invoice')",
            "required": True
        },
        "docname": {
            "type": "string",
            "description": "The unique name or ID of the document (e.g., 'ACC-SINV-2026-00001')",
            "required": True
        },
        "action": {
            "type": "string",
            "description": "The action to perform: 'cancel', 'submit', 'update', or 'delete'",
            "required": True
        },
        "data": {
            "type": "string",
            "description": "JSON string of fields and values to update if action is 'update'",
            "required": False
        }
    },
    func=manage_erp_document
)