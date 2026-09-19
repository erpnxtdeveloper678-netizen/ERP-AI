import frappe
from erp_ai.ai.decorators import ai_tool
from erp_ai.ai.tools._security import (
    validate_doctype,
    validate_fieldname,
    validate_filters,
    check_permission,
    parse_filters,
)



# Real Dashboard Chart schema (verified against frappe/frappe's
# dashboard_chart.py controller - the original repo's system prompt had the
# 'type' and 'chart_type' meanings backwards, which meant AI-created charts
# would fail validation or misrender):
#
#   document_type            -> the DocType the chart reads from
#   type                     -> VISUAL style: Line | Bar | Percentage | Pie | Donut
#   chart_type               -> AGGREGATION mode: Count | Sum | Average | Group By
#   based_on                 -> date field, time-series mode only
#   value_based_on            -> value field, time-series Sum/Average only
#   timeseries / time_interval -> time-series mode only
#   group_by_based_on         -> field to group by, group_by mode only
#   group_by_type              -> Count | Sum | Average, group_by mode only
#   aggregate_function_based_on -> value field, group_by Sum/Average only

ALLOWED_VISUAL_TYPES = {"Line", "Bar", "Percentage", "Pie", "Donut"}
ALLOWED_AGGREGATES = {"Count", "Sum", "Average"}
ALLOWED_TIME_INTERVALS = {"Daily", "Weekly", "Monthly", "Quarterly", "Yearly"}

# Number Card schema (the KPI "card" widgets, e.g. "Total Sales Today"),
# based on frappe/frappe's number_card doctype:
#
#   type                      -> "Document Type" (the only mode we expose here;
#                                 Report/Custom cards run a saved report or a
#                                 whitelisted Python method instead of a DocType
#                                 query, which is out of scope for an AI tool)
#   document_type             -> the DocType the card counts/aggregates
#   function                  -> Count | Sum | Average | Minimum | Maximum
#   aggregate_function_based_on -> value field, required for Sum/Average/Minimum/Maximum
#   filters_json               -> same list-of-conditions format as list view filters
#   show_percentage_stats      -> if 1, shows +/- change vs the previous stats_time_interval
#   stats_time_interval         -> Daily | Weekly | Monthly | Yearly, only used with the above
#
# IMPORTANT: verify this against the actual installed Frappe version once a
# bench is available (`bench --site <site> console` ->
# frappe.get_meta("Number Card").fields) - the fieldnames above are based on
# the stable, long-standing "Doctype Dashboard View" Number Card feature but
# have not been runtime-verified in this sandbox (no Frappe install here).
ALLOWED_CARD_FUNCTIONS = {"Count", "Sum", "Average", "Minimum", "Maximum"}


@ai_tool(
    name="create_report",
    description=(
        "Create and save a Report Builder report (a saved, filterable list view) on an "
        "existing DocType. Raw-SQL Query Reports and Script Reports are not offered here "
        "since they execute arbitrary code every time anyone opens them - ask a System "
        "Manager to create those directly in the desk UI if one is truly needed."
    ),
    parameters={
        "report_title": {"type": "string", "required": True},
        "ref_doctype": {"type": "string", "required": True, "description": "DocType the report is based on."},
        "module": {"type": "string"},
    },
)
def create_report(report_title, ref_doctype, module=None, **kwargs):
    if not frappe.has_permission("Report", "create"):
        frappe.throw("You do not have permission to create reports.")

    validate_doctype(ref_doctype)
    check_permission(ref_doctype, "read")

    if frappe.db.exists("Report", {"report_name": report_title}):
        frappe.throw(f"A report named '{report_title}' already exists.")

    doc = frappe.get_doc({
        "doctype": "Report",
        "report_name": report_title,
        "report_type": "Report Builder",
        "ref_doctype": ref_doctype,
        "is_standard": "No",
        "module": module or frappe.get_meta(ref_doctype).module or "Core",
    })
    doc.insert()
    return {"status": "success", "report_name": doc.name}


@ai_tool(
    name="create_dashboard_chart",
    description=(
        "Create a Dashboard Chart on a DocType, for statistics/analysis. "
        "Two modes: 'time_series' (a trend of count/sum/average over a date field, e.g. "
        "'monthly sales total') or 'group_by' (count/sum/average grouped by a field, "
        "e.g. 'sales by customer')."
    ),
    parameters={
        "chart_name": {"type": "string", "required": True},
        "doctype": {"type": "string", "required": True},
        "mode": {"type": "string", "required": True, "description": "time_series | group_by"},
        "aggregate": {"type": "string", "description": "Count, Sum, or Average. Default Count."},
        "value_field": {"type": "string", "description": "Numeric field to sum/average. Required unless aggregate is Count."},
        "date_field": {"type": "string", "description": "Date field for time_series mode, e.g. posting_date."},
        "group_by_field": {"type": "string", "description": "Field to group by, for group_by mode."},
        "time_interval": {"type": "string", "description": "Daily, Weekly, Monthly, Quarterly, Yearly. Default Monthly."},
        "visual_type": {"type": "string", "description": "Line, Bar, Percentage, Pie, Donut. Default Bar."},
        "module": {"type": "string"},
    },
)
def create_dashboard_chart(chart_name, doctype, mode, aggregate="Count", value_field=None,
                            date_field=None, group_by_field=None, time_interval="Monthly",
                            visual_type="Bar", module=None, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "read")
    if not frappe.has_permission("Dashboard Chart", "create"):
        frappe.throw("You do not have permission to create dashboard charts.")

    # Idempotent instead of a hard failure: if the model retries the same
    # request (e.g. after a transient error, or the user re-confirming),
    # reuse the existing chart rather than derailing the whole multi-step
    # dashboard build with an error the model has to recover from.
    if frappe.db.exists("Dashboard Chart", chart_name):
        return {
            "status": "exists",
            "chart_name": chart_name,
            "message": f"Dashboard Chart '{chart_name}' already exists - reusing it as-is.",
        }

    mode = (mode or "").lower().strip()
    aggregate = aggregate if aggregate in ALLOWED_AGGREGATES else "Count"
    visual_type = visual_type if visual_type in ALLOWED_VISUAL_TYPES else "Bar"
    time_interval = time_interval if time_interval in ALLOWED_TIME_INTERVALS else "Monthly"

    chart_doc = {
        "doctype": "Dashboard Chart",
        "chart_name": chart_name,
        "document_type": doctype,
        "type": visual_type,
        "module": module or frappe.get_meta(doctype).module or "Core",
        # Dashboard Chart has `filters_json` as a mandatory field even when
        # there are no filters - Frappe rejects the insert with "Value
        # missing for Dashboard Chart: Filters JSON" if it's left unset.
        "filters_json": "[]",
    }

    if mode == "time_series":
        if not date_field:
            frappe.throw("`date_field` is required for time_series charts.")
        validate_fieldname(doctype, date_field)

        if aggregate != "Count":
            if not value_field:
                frappe.throw("`value_field` is required for Sum/Average time_series charts.")
            validate_fieldname(doctype, value_field)

        chart_doc.update({
            "chart_type": aggregate,
            "based_on": date_field,
            "value_based_on": value_field,
            "timeseries": 1,
            "time_interval": time_interval,
            # Required alongside timeseries=1 - without it the chart has no
            # window to compute over. "Last Year" gives the widest default
            # view; the model can still ask the user for a narrower one.
            "timespan": "Last Year",
        })

    elif mode == "group_by":
        if not group_by_field:
            frappe.throw("`group_by_field` is required for group_by charts.")
        validate_fieldname(doctype, group_by_field)

        if aggregate != "Count":
            if not value_field:
                frappe.throw("`value_field` is required for Sum/Average group_by charts.")
            validate_fieldname(doctype, value_field)

        chart_doc.update({
            "chart_type": "Group By",
            "group_by_based_on": group_by_field,
            "group_by_type": aggregate,
            "aggregate_function_based_on": value_field,
        })

    else:
        frappe.throw("`mode` must be either 'time_series' or 'group_by'.")

    doc = frappe.get_doc({k: v for k, v in chart_doc.items() if v is not None})
    doc.insert()
    return {"status": "success", "chart_name": doc.name}


def _filters_dict_to_json(doctype, filters):
    """Number Card / Dashboard Chart `filters_json` uses the list-view filter
    format (a list of [fieldname, operator, value] conditions), not the plain
    {field: value} dict our other tools use. We still validate keys through
    validate_filters (real fields only, permission-safe), then convert."""
    clean = validate_filters(doctype, filters)
    return frappe.as_json([[field, "=", value] for field, value in clean.items()])


@ai_tool(
    name="create_number_card",
    description=(
        "Create a Number Card - a single-number KPI widget for a Dashboard, e.g. "
        "'Total Sales Today', 'Open Purchase Orders', 'Average Order Value'. "
        "Counts/aggregates over a single DocType, optionally filtered. For a trend or "
        "breakdown instead of one number, use create_dashboard_chart."
    ),
    parameters={
        "card_name": {"type": "string", "required": True, "description": "Label shown on the card."},
        "doctype": {"type": "string", "required": True},
        "function": {"type": "string", "description": "Count | Sum | Average | Minimum | Maximum. Default Count."},
        "value_field": {"type": "string", "description": "Numeric field to aggregate. Required unless function is Count."},
        "filters": {"type": "object", "description": "Optional {field: value} filters, e.g. {'status': 'Open'}."},
        "show_percentage_stats": {"type": "boolean", "description": "Show +/- change vs the previous period. Default false."},
        "stats_time_interval": {"type": "string", "description": "Daily | Weekly | Monthly | Yearly. Only used with show_percentage_stats."},
        "module": {"type": "string"},
    },
)
def create_number_card(card_name, doctype, function="Count", value_field=None, filters=None,
                        show_percentage_stats=False, stats_time_interval="Monthly",
                        module=None, **kwargs):
    validate_doctype(doctype)
    check_permission(doctype, "read")
    if not frappe.has_permission("Number Card", "create"):
        frappe.throw("You do not have permission to create number cards.")

    if frappe.db.exists("Number Card", card_name):
        return {
            "status": "exists",
            "card_name": card_name,
            "message": f"Number Card '{card_name}' already exists - reusing it as-is.",
        }

    function = function if function in ALLOWED_CARD_FUNCTIONS else "Count"
    if function != "Count":
        if not value_field:
            frappe.throw(f"`value_field` is required for the '{function}' function.")
        validate_fieldname(doctype, value_field)

    stats_time_interval = stats_time_interval if stats_time_interval in ALLOWED_TIME_INTERVALS else "Monthly"

    card_doc = {
        "doctype": "Number Card",
        "label": card_name,
        "type": "Document Type",
        "document_type": doctype,
        "function": function,
        "aggregate_function_based_on": value_field,
        "filters_json": _filters_dict_to_json(doctype, filters),
        "module": module or frappe.get_meta(doctype).module or "Core",
        "show_percentage_stats": 1 if show_percentage_stats else 0,
    }
    if show_percentage_stats:
        card_doc["stats_time_interval"] = stats_time_interval

    doc = frappe.get_doc({k: v for k, v in card_doc.items() if v is not None})
    doc.insert()

    return {"status": "success", "card_name": doc.name}


@ai_tool(
    name="create_dashboard",
    description=(
        "Create a Dashboard and attach one or more existing Dashboard Charts and/or "
        "Number Cards to it. Use create_dashboard_chart / create_number_card first for "
        "any chart or card that doesn't exist yet. At least one of chart_names or "
        "card_names must be given. If a Dashboard with this name already exists, the "
        "given charts/cards are merged into it (no duplicates) instead of failing."
    ),
    parameters={
        "dashboard_name": {"type": "string", "required": True},
        "chart_names": {"type": "array", "description": "Names of existing Dashboard Charts to attach."},
        "card_names": {"type": "array", "description": "Names of existing Number Cards to attach."},
        "module": {"type": "string"},
    },
)
def create_dashboard(dashboard_name, chart_names=None, card_names=None, module=None, **kwargs):
    if not (chart_names or card_names):
        frappe.throw("Provide at least one of `chart_names` or `card_names`.")

    # Validate every referenced chart/card BEFORE touching the Dashboard record,
    # so a bad name never leaves a half-built/empty Dashboard behind.
    charts = []
    for chart_name in (chart_names or []):
        if not frappe.db.exists("Dashboard Chart", chart_name):
            frappe.throw(f"Dashboard Chart '{chart_name}' does not exist. Create it first with create_dashboard_chart.")
        if not frappe.has_permission("Dashboard Chart", "read", doc=chart_name):
            frappe.throw(f"You do not have permission to read chart '{chart_name}'.")
        charts.append(chart_name)

    cards = []
    for card_name in (card_names or []):
        if not frappe.db.exists("Number Card", card_name):
            frappe.throw(f"Number Card '{card_name}' does not exist. Create it first with create_number_card.")
        if not frappe.has_permission("Number Card", "read", doc=card_name):
            frappe.throw(f"You do not have permission to read card '{card_name}'.")
        cards.append(card_name)

    if frappe.db.exists("Dashboard", dashboard_name):
        # Idempotent instead of a hard failure: if a Dashboard with this name
        # already exists (e.g. the model retried after an earlier error, or
        # the user is extending a dashboard from a previous request), attach
        # any charts/cards that aren't on it yet rather than failing outright.
        if not frappe.has_permission("Dashboard", "write", doc=dashboard_name):
            frappe.throw(f"You do not have permission to modify dashboard '{dashboard_name}'.")

        doc = frappe.get_doc("Dashboard", dashboard_name)
        existing_charts = {row.chart for row in doc.charts}
        existing_cards = {row.card for row in doc.cards}

        added_charts = [c for c in charts if c not in existing_charts]
        added_cards = [c for c in cards if c not in existing_cards]

        for chart_name in added_charts:
            doc.append("charts", {"chart": chart_name})
        for card_name in added_cards:
            doc.append("cards", {"card": card_name})

        if added_charts or added_cards:
            doc.save()

        return {
            "status": "exists",
            "dashboard_name": doc.name,
            "added_charts": added_charts,
            "added_cards": added_cards,
            "message": (
                f"Dashboard '{doc.name}' already existed - added "
                f"{len(added_charts)} new chart(s) and {len(added_cards)} new card(s) to it."
            ),
        }

    if not frappe.has_permission("Dashboard", "create"):
        frappe.throw("You do not have permission to create dashboards.")

    doc = frappe.get_doc({
        "doctype": "Dashboard",
        "dashboard_name": dashboard_name,
        "module": module or "Core",
        "is_default": 0,
        "charts": [{"chart": c} for c in charts],
        "cards": [{"card": c} for c in cards],
    })
    doc.insert()

    return {"status": "success", "dashboard_name": doc.name}


@ai_tool(
    name="list_reports",
    description=(
        "List saved Reports the current user is allowed to see (Report Builder, "
        "Query Report, and Script Report alike), optionally filtered to those built "
        "on a given DocType. Use this to find the exact `report_name` to pass to "
        "run_report when you don't already know it."
    ),
    parameters={
        "ref_doctype": {"type": "string", "description": "Only list reports built on this DocType."},
        "limit": {"type": "integer", "description": "Max results, capped at 100. Default 50."},
    },
)
def list_reports(ref_doctype=None, limit=50, **kwargs):
    filters = {"disabled": 0}
    if ref_doctype:
        validate_doctype(ref_doctype)
        filters["ref_doctype"] = ref_doctype

    limit = max(1, min(int(limit or 50), 100))

    # frappe.get_list on the "Report" doctype itself already applies the
    # current user's Report-level permissions (including each report's own
    # `roles` child table) - exactly like the Report List view in the desk UI.
    return frappe.get_list(
        "Report",
        filters=filters,
        fields=["name", "report_name", "report_type", "ref_doctype", "module"],
        order_by="report_name asc",
        limit_page_length=limit,
    )


@ai_tool(
    name="run_report",
    description=(
        "Run an existing saved Report and return its columns and rows - e.g. to "
        "answer 'show me the Sales Register for this month' or to read the data "
        "behind a report you or a System Manager already set up. This does not "
        "create or change any report logic; it executes the report exactly as "
        "opening it in the desk UI and clicking Run would, with the current user's "
        "normal report and DocType permissions applied. Use list_reports first if "
        "you don't know the exact report name, or analyze_data instead if you just "
        "want an ad-hoc count/sum/group-by over a DocType rather than a named report."
    ),
    parameters={
        "report_name": {"type": "string", "required": True, "description": "Exact name of an existing Report."},
        "filters": {
            "type": "object",
            "description": "Optional {field: value} filters, using whatever filter fields this report exposes.",
        },
        "limit": {"type": "integer", "description": "Max rows to return, capped at 500. Default 100."},
    },
)
def run_report(report_name, filters=None, limit=100, **kwargs):
    if not report_name or not frappe.db.exists("Report", report_name):
        frappe.throw(f"Unknown Report: '{report_name}'.")

    # Gate on the Report doc's own permissions first - same as whether the
    # desk UI would even let the user open this report from the Report List.
    check_permission("Report", "read", doc=report_name)

    report = frappe.get_doc("Report", report_name)

    clean_filters = parse_filters(filters)
    limit = max(1, min(int(limit or 100), 500))

    from frappe.desk.query_report import run as run_query_report

    result = run_query_report(report_name=report_name, filters=clean_filters or None)

    all_rows = result.get("result") or []
    return {
        "report_name": report_name,
        "report_type": report.report_type,
        "columns": result.get("columns", []),
        "row_count": len(all_rows),
        "rows": all_rows[:limit],
        "truncated": len(all_rows) > limit,
    }

