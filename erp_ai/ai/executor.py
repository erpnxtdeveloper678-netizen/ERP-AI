import frappe
import json
from erp_ai.ai.registry import get_tool

def execute_tool(name: str, args: dict = None):
    """
    Dynamically executes a tool registered in the AI Registry.
    """
    if args is None:
        args = {}
        
    # 1. البحث عن الأداة داخل الـ Registry
    tool = get_tool(name)
    if not tool:
        raise ValueError(f"Tool '{name}' is not registered in the AI Registry.")
        
    # 2. جلب الدالة (Python Function) المرتبطة بالأداة
    func = tool.get("function")
    if not func:
        raise ValueError(f"No executable function found for tool '{name}'.")
        
    # 3. معالجة وتطهير الـ args لمنع خطأ Marshal في Python 3.12
    clean_args = {}
    try:
        if args:
            # تحويل الـ args لـ JSON ثم فكها مجدداً يحول أي كائنات معقدة (Protobuf Map) إلى Dict بايثون عادي صريح
            serialized = json.dumps(args)
            clean_args = json.loads(serialized)
    except Exception:
        # إذا فشل التحويل، نعتمد على الـ args الأصلية كخطة بديلة
        clean_args = args

    # 4. تنفيذ الدالة وتمرير المتغيرات النظيفة
    try:
        # تنفيذ الدالة في سياق Frappe وتمرير الـ clean_args
        result = func(**clean_args)
        return result
    except Exception as e:
        # تسجيل الخطأ في Frappe Error Log لمراجعته
        frappe.log_error(
            title=f"ERP AI Executor Error ({name})",
            message=frappe.get_traceback()
        )
        raise e