from collections import defaultdict

import frappe
from erp_ai.ai.decorators import ai_tool
from erp_ai.ai.tools._security import (
    validate_doctype,
    validate_fieldname,
    validate_fields,
    validate_filters,
    validate_order_by,
    check_permission,
    AGGREGATE_FUNCTIONS,
)

# Frappe's ORM (get_list/get_all/get_value) rejects SQL function calls written
# as plain strings in `fields` on current versions - e.g. "count(name) as
# value" raises "SQL functions are not allowed as strings in SELECT" (this
# landed alongside the CVE-2025-30212 / CVE-2025-30217 SQL-injection fixes).
# Aggregates must be passed as a dict instead:
#   {"COUNT": "name", "as": "value"}   ->  COUNT(`name`) AS `value`
# See: https://github.com/frappe/frappe/pull/32381
SQL_FUNCTION = {"count": "COUNT", "sum": "SUM", "avg": "AVG", "min": "MIN", "max": "MAX"}

PERIODS = ("day", "week", "month", "quarter", "year")


def _agg_field(fn, field, alias):
    """Build a Frappe-ORM-safe aggregate field dict, e.g. {'SUM': 'grand_total', 'as': 'value'}."""
    return {SQL_FUNCTION[fn]: field or "*", "as": alias}


def _default_order_field(doctype):
    try:
        meta = frappe.get_meta(doctype)
        fieldnames = {d.fieldname for d in meta.fields}
        for f in ("posting_date", "transaction_date", "date"):
            if f in fieldnames:
                return f
    except Exception:
        pass
    return "creation"


def _period_key(d, period):
    d = frappe.utils.getdate(d)
    if period == "day":
        return d.isoformat()
    if period == "week":
        iso = d.isocalendar()
        return f"{iso[0]:04d}-W{iso[1]:02d}"
    if period == "month":
        return f"{d.year:04d}-{d.month:02d}"
    if period == "quarter":
        return f"{d.year:04d}-Q{(d.month - 1) // 3 + 1}"
    return f"{d.year:04d}"  # year


def _grouped_by_period(doctype, clean_filters, group_by, agg, value_field, period, limit):
    """
    Buckets a date/datetime field into day/week/month/quarter/year totals.
    Rather than asking the DB to truncate dates (function support/syntax varies
    by DB backend and Frappe version - exactly what broke the plain aggregate
    fields above), we pull real, permission-filtered per-day aggregates from
    frappe.get_list() - a bounded number of rows even over a multi-year range -
    then bucket them into periods in Python, where the logic is portable and
    easy to verify. count/sum bucket by re-summing; avg is recomputed from
    summed totals/counts (not by averaging daily averages, which would be
    mathematically wrong); min/max bucket by taking min/max of the daily
    min/max values, which is correct.
    """
    day_fields = [f"{group_by} as group_field"]
    if agg in ("sum", "avg"):
        day_fields.append(_agg_field("sum", value_field, "total"))
    if agg in ("avg", "count"):
        day_fields.append(_agg_field("count", "name", "cnt"))
    if agg in ("min", "max"):
        day_fields.append(_agg_field(agg, value_field, "val"))

    raw = frappe.get_list(
        doctype, filters=clean_filters, fields=day_fields,
        group_by=group_by, order_by=f"{group_by} asc",
        limit_page_length=3660,  # ~10 years of daily buckets, plenty of headroom
    )

    sums, counts, vals = defaultdict(float), defaultdict(int), defaultdict(list)
    for row in raw:
        if row.group_field is None:
            continue
        key = _period_key(row.group_field, period)
        if agg in ("sum", "avg"):
            sums[key] += float(row.total or 0)
        if agg in ("avg", "count"):
            counts[key] += int(row.cnt or 0)
        if agg in ("min", "max"):
            if row.val is not None:
                vals[key].append(row.val)

    if agg == "sum":
        data = [{"group_field": k, "value": sums[k]} for k in sorted(sums)]
    elif agg == "count":
        data = [{"group_field": k, "value": counts[k]} for k in sorted(counts)]
    elif agg == "avg":
        keys = sorted(set(sums) | set(counts))
        data = [{"group_field": k, "value": (sums[k] / counts[k] if counts.get(k) else 0)} for k in keys]
    else:
        fn = min if agg == "min" else max
        data = [{"group_field": k, "value": fn(v)} for k, v in sorted(vals.items())]

    return data[-limit:] if limit else data


@ai_tool(
    name="analyze_data",
    description=(
        "Run aggregate analysis on ERPNext data: count, sum, avg, min, max, "
        "group-by totals (optionally bucketed by day/week/month/quarter/year - "
        "e.g. 'total sales per month'), distinct values, or first/last/list "
        "lookups. Every field name is checked against the DocType's real "
        "schema and every result is filtered by the current user's ERPNext "
        "permissions, exactly like the desk UI - there is no raw-SQL escape "
        "hatch. Line-item data (e.g. items sold) lives on the child DocType "
        "directly, e.g. doctype='Sales Invoice Item' with group_by='item_code', "
        "field='qty', aggregate='sum' - you do not need to go through the "
        "parent 'Sales Invoice' doctype for that. If you're not certain of the "
        "exact DocType name, call find_doctype first - a wrong-but-existing "
        "DocType returns 0/empty results, not an error. If you're not certain "
        "of an exact field name (e.g. the status field might be called "
        "'status', 'freight_status', 'docstatus', etc depending on the "
        "DocType), call get_doctype_meta first instead of guessing - a wrong "
        "field name is rejected with an error, so checking first avoids a "
        "failed call the user can see."
    ),
    parameters={
        "doctype": {"type": "string", "required": True},
        "operation": {
            "type": "string",
            "required": True,
            "description": "count | sum | avg | min | max | group | distinct | first | last | list",
        },
        "field": {"type": "string", "description": "Field to aggregate/select (required for sum/avg/min/max/distinct)."},
        "fields": {"type": "array", "description": "Fields to return for 'list' / 'first' / 'last'."},
        "filters": {"type": "object"},
        "group_by": {"type": "string", "description": "Field to group by (required for 'group')."},
        "aggregate": {"type": "string", "description": "For 'group': sum | count | avg | min | max. Default sum."},
        "period": {
            "type": "string",
            "description": (
                "Optional, only for 'group' when group_by is a Date/Datetime field: "
                "day | week | month | quarter | year. Use this for 'total sales by "
                "month' style questions instead of grouping by the raw date."
            ),
        },
        "order_by": {"type": "string"},
        "limit": {"type": "integer", "description": "Capped at 500 (100 for 'group'/'distinct')."},
    },
)
def analyze_data(doctype, operation, field=None, fields=None, filters=None,
                  group_by=None, aggregate="sum", period=None, order_by=None,
                  limit=20, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "read")

    operation = (operation or "").lower().strip()
    limit = max(1, min(int(limit or 20), 500))
    clean_filters = validate_filters(doctype, filters)

    if operation == "count":
        result = frappe.get_list(doctype, filters=clean_filters, fields=[_agg_field("count", "name", "value")])
        return {"operation": "count", "value": (result[0].value if result else 0)}

    if operation in ("sum", "avg", "min", "max"):
        if not field:
            frappe.throw(f"`field` is required for '{operation}'.")
        validate_fieldname(doctype, field)
        result = frappe.get_list(doctype, filters=clean_filters, fields=[_agg_field(operation, field, "value")])
        value = result[0].value if result else 0
        return {"operation": operation, "field": field, "value": value or 0}

    if operation == "distinct":
        if not field:
            frappe.throw("`field` is required for 'distinct'.")
        validate_fieldname(doctype, field)
        result = frappe.get_list(
            doctype, filters=clean_filters,
            fields=[field],
            distinct=1,
            limit_page_length=min(limit, 100),
        )
        return {"operation": "distinct", "field": field, "values": [r[field] for r in result]}

    if operation == "group":
        if not group_by:
            frappe.throw("`group_by` is required for 'group'.")
        validate_fieldname(doctype, group_by)

        agg = (aggregate or "sum").lower()
        if agg not in AGGREGATE_FUNCTIONS:
            frappe.throw(f"Unsupported aggregate: '{agg}'. Use one of {sorted(AGGREGATE_FUNCTIONS)}.")

        value_field = None
        if agg != "count":
            value_field = field or "name"
            validate_fieldname(doctype, value_field)

        if period:
            period = period.lower().strip()
            if period not in PERIODS:
                frappe.throw(f"`period` must be one of: {', '.join(PERIODS)}.")
            meta = frappe.get_meta(doctype)
            df = meta.get_field(group_by)
            if not df or df.fieldtype not in ("Date", "Datetime"):
                frappe.throw(f"`period` requires `group_by` to be a Date/Datetime field; "
                             f"'{group_by}' is {df.fieldtype if df else 'not a real field'}.")
            data = _grouped_by_period(doctype, clean_filters, group_by, agg, value_field, period, min(limit, 100))
            return {"operation": "group", "group_by": group_by, "period": period,
                    "aggregate": agg, "field": value_field, "data": data}

        agg_field = _agg_field(agg, value_field or "name", "value")
        result = frappe.get_list(
            doctype,
            filters=clean_filters,
            fields=[f"{group_by} as group_field", agg_field],
            group_by=group_by,
            order_by="value desc",
            limit_page_length=min(limit, 100),
        )
        return {"operation": "group", "group_by": group_by, "aggregate": agg, "field": value_field, "data": result}

    if operation in ("first", "last", "list"):
        select_fields = validate_fields(doctype, fields)

        if operation == "list":
            clean_order = validate_order_by(doctype, order_by)
            page_limit = limit
        else:
            of = order_by or _default_order_field(doctype)
            direction = "asc" if operation == "first" else "desc"
            clean_order = validate_order_by(doctype, f"{of} {direction}")
            page_limit = 1

        return frappe.get_list(
            doctype, filters=clean_filters, fields=select_fields,
            order_by=clean_order, limit_page_length=page_limit,
        )

    frappe.throw(
        f"Unsupported operation: '{operation}'. Use one of: "
        "count, sum, avg, min, max, group, distinct, first, last, list."
    )
    