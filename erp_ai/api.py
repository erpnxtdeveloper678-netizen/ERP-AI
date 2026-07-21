import json
import frappe
import csv
import io

@frappe.whitelist()
def ask(message, conversation=None, file_data=None, file_name=None):
    if conversation:
        try:
            conversation = json.loads(conversation)
        except Exception:
            conversation = []
    else:
        conversation = []

    # دمج محتوى الملف المرفق مع رسالة المستخدم إذا وجد
    full_message = message or ""
    if file_data:
        full_message = f"[مرفق ملف: {file_name}]\nمحتوى الملف:\n{file_data}\n\nسؤال المستخدم:\n{full_message}"

    from erp_ai.ai.service import ask_ai
    
    # بما أن الـ ask_ai بيرجع Generator (بسبب الـ yield)، 
    # هنجمع النص أو نعمل هاندلينگ للـ streaming لو متاح، 
    # أو نخليه يرجع النص كاملاً لو الـ API محتاج Response مباشر.
    try:
        response_generator = ask_ai(message=full_message, conversation=conversation)
        # لو الـ ask_ai بترجع generator، بنجمع الكتل (chunks) مع بعضها
        if hasattr(response_generator, "__iter__") and not isinstance(response_generator, (str, dict, list)):
            reply = "".join([chunk for chunk in response_generator if chunk])
        else:
            reply = response_generator
    except Exception as e:
        reply = f"Error: {str(e)}"
    
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
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "CSV Export Error")
        return {"status": "error", "message": str(e)}