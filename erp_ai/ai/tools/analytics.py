import json
import frappe
from frappe.query_builder import DocType
from pypika.functions import Count, Sum, Avg
from erp_ai.ai.decorators import ai_tool


def apply_filters(query, table, filters=None):
    # التأكد تماماً أن الـ filters كائن ديشنري وليست نصاً قادماً بطريق الخطأ من الـ AI
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except Exception:
            filters = {}
            
    filters = filters or {}
    
    if not isinstance(filters, dict):
        return query

    for key, value in filters.items():
        # معالجة ذكية للفلاتر المتقدمة لمنع الـ SQL Syntax Error
        if isinstance(value, (list, tuple)) and len(value) == 2 and isinstance(value[0], str) and value[0].lower() in ["in", "not in"]:
            operator = value[0].lower()
            actual_value = value[1]
            if operator == "in":
                query = query.where(table[key].isin(actual_value))
            elif operator == "not in":
                query = query.where(table[key].notin(actual_value))
        elif isinstance(value, (list, tuple)):
            query = query.where(table[key].isin(value))
        else:
            query = query.where(table[key] == value)
    return query


def get_default_order_field(doctype):
    try:
        meta = frappe.get_meta(doctype)
        fields = [d.fieldname for d in meta.fields]
        for f in ("posting_date", "transaction_date", "date", "creation"):
            if f == "creation" or f in fields:
                return f
    except Exception:
        pass
    return "creation"


@ai_tool(
    name="analyze_data",
    description="Analyze ERPNext data with operations like count, sum, avg, group, etc.",
    parameters={
        "doctype": {"type": "string", "required": True},
        "operation": {"type": "string", "required": True},
        "field": {"type": "string"},
        "fields": {"type": "array"},
        "filters": {"type": "object"},
        "group_by": {"type": "string"},
        "order_by": {"type": "string"},
        "limit": {"type": "integer"},
    },
)
def analyze_data(
    doctype,
    operation,
    field=None,
    fields=None,
    filters=None,
    group_by=None,
    order_by=None,
    limit=20,
    **kwargs
):
    try:
        # فحص إضافي آمن لتنظيف الفلاتر إذا جاءت بصيغة نصية
        if isinstance(filters, str):
            try:
                filters = json.loads(filters)
            except Exception:
                filters = {}

        filters = filters or {}
        table = DocType(doctype)

        # حماية وتأمين الـ kwargs المبعوثة من الـ SDK بدون مسافات تحسباً لأي لغبطة
        order_by = order_by or kwargs.get("orderby")
        group_by = group_by or kwargs.get("groupby")

        if operation == "count":
            q = frappe.qb.from_(table).select(Count("*").as_("value"))
            q = apply_filters(q, table, filters)
            r = q.run(as_dict=True)
            return {"operation": "count", "value": r[0]["value"] if r else 0}

        if operation == "sum":
            q = frappe.qb.from_(table).select(Sum(table[field]).as_("value"))
            q = apply_filters(q, table, filters)
            r = q.run(as_dict=True)
            return {"operation": "sum", "field": field, "value": r[0]["value"] or 0}

        if operation == "avg":
            q = frappe.qb.from_(table).select(Avg(table[field]).as_("value"))
            q = apply_filters(q, table, filters)
            r = q.run(as_dict=True)
            return {"operation": "avg", "field": field, "value": r[0]["value"] or 0}

        if operation == "exists":
            return {"exists": frappe.db.exists(doctype, filters) is not None}

        if operation == "first":
            of = get_default_order_field(doctype)
            return frappe.get_all(
                doctype,
                filters=filters,
                fields=fields or ["*"],
                order_by=f"{of} asc, creation asc",
                limit_page_length=1,
            )

        if operation == "last":
            of = get_default_order_field(doctype)
            return frappe.get_all(
                doctype,
                filters=filters,
                fields=fields or ["*"],
                order_by=f"{of} desc, creation desc",
                limit_page_length=1,
            )

        if operation == "max":
            return frappe.get_all(
                doctype,
                filters=filters,
                fields=["*"],
                order_by=f"{field} desc" if field else "creation desc",
                limit_page_length=1,
            )

        if operation == "min":
            return frappe.get_all(
                doctype,
                filters=filters,
                fields=["*"],
                order_by=f"{field} asc" if field else "creation asc",
                limit_page_length=1,
            )

        if operation == "distinct":
            return frappe.db.sql(
                f"SELECT DISTINCT `{field}` FROM `tab{doctype}`",
                as_dict=True,
            )

        if operation == "group":
            group_by = group_by or "customer"
            field = field or "grand_total"
            agg = kwargs.get("aggregate", "sum")
            
            if agg == "sum":
                sql = f"""SELECT `{group_by}` as group_field, SUM(`{field}`) as value
FROM `tab{doctype}`
GROUP BY `{group_by}`
ORDER BY value DESC
LIMIT {int(limit)}"""
            else:
                sql = f"""SELECT `{group_by}` as group_field, COUNT(*) as value
FROM `tab{doctype}`
GROUP BY `{group_by}`
ORDER BY value DESC
LIMIT {int(limit)}"""
            return frappe.db.sql(sql, as_dict=True)

        return frappe.get_all(
            doctype,
            filters=filters,
            fields=fields or ["name"],
            order_by=order_by or "creation desc",
            limit_page_length=limit,
        )
    except Exception as e:
        frappe.log_error(title="ERP AI Tool Execution Error", message=str(e))
        return {"error": str(e)}