"""
Inventory / stock tools (ERPNext's Stock module: Bin, Item, Stock Entry,
Stock Ledger Entry).

Every tool here is registered with providers=["claude"] (see decorators.py /
registry.py) - none of them are exposed to the Gemini provider.

Follows the exact same security model as tools/documents.py: the AI model is
an untrusted caller acting as frappe.session.user, every doctype/fieldname is
validated with the shared helpers in tools/_security.py, and every action
goes through frappe's normal has_permission() checks - nothing here uses
ignore_permissions or raw SQL. If the erpnext app (and therefore these
doctypes) isn't installed on the site, validate_doctype() raises a clear
"Unknown DocType" error rather than failing obscurely.
"""

import frappe
from erp_ai.ai.decorators import ai_tool
from erp_ai.ai.tools._security import (
    validate_doctype,
    check_permission,
    get_writable_fieldnames,
)


def _resolve_item_code(item_code_or_name):
    """Accept either an exact Item code (the primary key) or a human name/
    partial name, and resolve it to a real Item code. Users naturally refer
    to items by name (often in Arabic), not by their internal code, so a
    strict frappe.db.exists("Item", value) lookup alone fails for anything
    that isn't the exact code - this is the fix for that.

    Raises a clear frappe.throw() if there's no match or more than one
    equally-plausible match, instead of silently guessing.
    """
    value = (item_code_or_name or "").strip()
    if not value:
        frappe.throw("An item code or item name is required.")

    # 1) Exact match on the primary key (the normal/fast path).
    if frappe.db.exists("Item", value):
        return value

    # 2) Fall back to a name search (item_name, case-insensitive, partial).
    matches = frappe.get_list(
        "Item",
        filters=[["item_name", "like", f"%{value}%"]],
        fields=["item_code", "item_name"],
        limit_page_length=10,
    )
    if len(matches) == 1:
        return matches[0]["item_code"]
    if len(matches) > 1:
        options = ", ".join(f"{m['item_code']} ({m['item_name']})" for m in matches)
        frappe.throw(
            f"'{value}' matches more than one item - please specify the exact item_code: {options}."
        )

    frappe.throw(
        f"Unknown item: '{value}'. No Item exists with that code, and no Item name contains it. "
        "Use find_doctype or list_documents on doctype='Item' to search."
    )


@ai_tool(
    name="get_stock_balance",
    description=(
        "Get the current stock quantity of an Item, either in one specific "
        "warehouse or summed across every warehouse the user can see. Reads "
        "from the Bin doctype (ERPNext's live stock-balance table), the same "
        "source the Stock Balance report and item forms use."
    ),
    parameters={
        "item_code": {
            "type": "string", "required": True,
            "description": "Exact item code, OR the item's name/part of its name (e.g. as the user typed it) - it will be resolved automatically.",
        },
        "warehouse": {"type": "string", "description": "Optional. Omit to sum across all warehouses."},
    },
    providers=["claude"],
)
def get_stock_balance(item_code, warehouse=None, **kwargs):
    validate_doctype("Bin")
    check_permission("Bin", "read")

    item_code = _resolve_item_code(item_code)

    filters = {"item_code": item_code}
    if warehouse:
        if not frappe.db.exists("Warehouse", warehouse):
            frappe.throw(f"Unknown Warehouse: '{warehouse}'.")
        filters["warehouse"] = warehouse

    rows = frappe.get_list(
        "Bin",
        filters=filters,
        fields=["warehouse", "actual_qty", "reserved_qty", "projected_qty"],
        limit_page_length=200,
    )

    total = sum(float(r.actual_qty or 0) for r in rows)
    return {
        "item_code": item_code,
        "warehouse": warehouse,
        "total_actual_qty": total,
        "by_warehouse": rows,
    }


@ai_tool(
    name="get_low_stock_items",
    description=(
        "List Items whose current stock has fallen at or below their "
        "configured safety stock / reorder level - use this for 'what needs "
        "reordering' style questions. Compares each Item's `safety_stock` "
        "field against its live Bin balance (summed across warehouses, or "
        "just one warehouse if given)."
    ),
    parameters={
        "warehouse": {"type": "string", "description": "Optional. Restrict the stock check to one warehouse."},
        "limit": {"type": "integer", "description": "Max items to check/return, capped at 100. Default 20."},
    },
    providers=["claude"],
)
def get_low_stock_items(warehouse=None, limit=20, **kwargs):
    validate_doctype("Item")
    validate_doctype("Bin")
    check_permission("Item", "read")
    check_permission("Bin", "read")

    if warehouse and not frappe.db.exists("Warehouse", warehouse):
        frappe.throw(f"Unknown Warehouse: '{warehouse}'.")

    limit = max(1, min(int(limit or 20), 100))

    candidates = frappe.get_list(
        "Item",
        filters={"disabled": 0, "safety_stock": [">", 0]},
        fields=["item_code", "item_name", "safety_stock", "stock_uom"],
        order_by="modified desc",
        limit_page_length=500,  # scan a bounded pool; we only return `limit` low-stock hits
    )

    low_stock = []
    for item in candidates:
        bin_filters = {"item_code": item.item_code}
        if warehouse:
            bin_filters["warehouse"] = warehouse
        rows = frappe.get_list("Bin", filters=bin_filters, fields=["actual_qty"], limit_page_length=200)
        actual_qty = sum(float(r.actual_qty or 0) for r in rows)

        if actual_qty <= float(item.safety_stock or 0):
            low_stock.append({
                "item_code": item.item_code,
                "item_name": item.item_name,
                "stock_uom": item.stock_uom,
                "actual_qty": actual_qty,
                "safety_stock": item.safety_stock,
            })
        if len(low_stock) >= limit:
            break

    return {"warehouse": warehouse, "count": len(low_stock), "items": low_stock}


@ai_tool(
    name="create_stock_entry",
    description=(
        "Create a Stock Entry - a stock transfer, issue, receipt, or "
        "manufacture movement, the same as the Stock Entry form in ERPNext. "
        "Inserted as a DRAFT; use submit_document to submit it once the "
        "user confirms the details. Call get_doctype_meta with "
        "doctype='Stock Entry' first if you're unsure of extra fields (e.g. "
        "a target 'purpose'-specific field) beyond what's listed here."
    ),
    parameters={
        "stock_entry_type": {
            "type": "string", "required": True,
            "description": "e.g. 'Material Transfer', 'Material Issue', 'Material Receipt'.",
        },
        "items": {
            "type": "array", "required": True,
            "description": (
                "List of row objects, e.g. "
                "[{\"item_code\": \"ITM-001\", \"qty\": 5, \"s_warehouse\": \"Stores - X\", "
                "\"t_warehouse\": \"Finished Goods - X\"}]. Use s_warehouse (source) for "
                "issues/transfers and t_warehouse (target) for receipts/transfers."
            ),
        },
        "from_warehouse": {"type": "string", "description": "Optional default source warehouse for the whole entry."},
        "to_warehouse": {"type": "string", "description": "Optional default target warehouse for the whole entry."},
    },
    providers=["claude"],
)
def create_stock_entry(stock_entry_type, items, from_warehouse=None, to_warehouse=None, **kwargs):
    validate_doctype("Stock Entry")
    check_permission("Stock Entry", "create")

    if isinstance(items, str):
        import json
        try:
            items = json.loads(items)
        except Exception:
            frappe.throw("`items` must be a list of row objects.")
    if not isinstance(items, list) or not items:
        frappe.throw("`items` must be a non-empty list.")
    if len(items) > 100:
        frappe.throw("create_stock_entry supports at most 100 item rows per call.")

    allowed_row_fields = get_writable_fieldnames("Stock Entry Detail")

    doc = frappe.new_doc("Stock Entry")
    doc.stock_entry_type = stock_entry_type
    if from_warehouse:
        doc.from_warehouse = from_warehouse
    if to_warehouse:
        doc.to_warehouse = to_warehouse

    for row in items:
        if not isinstance(row, dict) or not row.get("item_code"):
            frappe.throw("Every row in `items` needs at least an `item_code`.")
        clean_row = {k: v for k, v in row.items() if k in allowed_row_fields}
        clean_row["item_code"] = _resolve_item_code(row["item_code"])
        doc.append("items", clean_row)

    doc.insert()
    return {"status": "success", "doctype": "Stock Entry", "name": doc.name, "stock_entry_type": doc.stock_entry_type}


@ai_tool(
    name="get_item_ledger",
    description=(
        "Get the stock movement history (Stock Ledger Entries) for one Item - "
        "every receipt, issue, and transfer that changed its balance, "
        "optionally scoped to one warehouse or date range. Use this to answer "
        "'what happened to the stock of X' style questions."
    ),
    parameters={
        "item_code": {
            "type": "string", "required": True,
            "description": "Exact item code, OR the item's name/part of its name - it will be resolved automatically.",
        },
        "warehouse": {"type": "string"},
        "from_date": {"type": "string", "description": "YYYY-MM-DD"},
        "to_date": {"type": "string", "description": "YYYY-MM-DD"},
        "limit": {"type": "integer", "description": "Capped at 200. Default 50."},
    },
    providers=["claude"],
)
def get_item_ledger(item_code, warehouse=None, from_date=None, to_date=None, limit=50, **kwargs):
    validate_doctype("Stock Ledger Entry")
    check_permission("Stock Ledger Entry", "read")

    item_code = _resolve_item_code(item_code)

    filters = {"item_code": item_code, "is_cancelled": 0}
    if warehouse:
        if not frappe.db.exists("Warehouse", warehouse):
            frappe.throw(f"Unknown Warehouse: '{warehouse}'.")
        filters["warehouse"] = warehouse
    if from_date:
        filters["posting_date"] = [">=", from_date]
    if to_date:
    
        if from_date:
            filters["posting_date"] = ["between", [from_date, to_date]]
        else:
            filters["posting_date"] = ["<=", to_date]

    limit = max(1, min(int(limit or 50), 200))

    rows = frappe.get_list(
        "Stock Ledger Entry",
        filters=filters,
        fields=[
            "posting_date", "posting_time", "voucher_type", "voucher_no",
            "actual_qty", "qty_after_transaction", "warehouse",
        ],
        order_by="posting_date desc, posting_time desc",
        limit_page_length=limit,
    )
    return {"item_code": item_code, "warehouse": warehouse, "count": len(rows), "entries": rows}
    