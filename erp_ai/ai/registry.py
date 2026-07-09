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
    as required by the new 'google-genai' Client SDK.
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


# =================================================================
# 🎯 دالة الاستعلام الفعلي من قاعدة البيانات المتأمنة ضد أخطاء الـ SDK
# =================================================================
def run_erp_query(doctype, fields=None, filters=None, limit=20, **kwargs):
    """
    دالة آمنة تتيح للـ AI جلب البيانات مباشرة من أي DocType في ERPNext
    محدثة ومؤمنة بالكامل لتفادي خطأ (unexpected keyword argument) من الـ SDK
    """
    try:
        # تأمين وقراءة البرامترز بأي صيغة يبعتها جيمناي (بـ Underscore أو بدونها)
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

        # لو طلب Sales Invoice نضمن رجوع الحقول الهامة للتحليل، وغير كدا يسحب الكل
        if not fields or fields == ["name"]:
            fields = ["name", "customer", "grand_total", "posting_date"] if doctype == "Sales Invoice" else ["*"]

        # تنفيذ الاستعلام الآمن من فرابيه
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

# =================================================================
# 🚀 تسجيل الأداة في الـ Registry مع إعلام الموديل بالبرامتر المتاحة
# =================================================================
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