"""Database-independent cleaning for the UCI Online Retail dataset."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import pandas as pd

COLUMN_ALIASES = {
    "InvoiceNo": "invoice_no", "Invoice No": "invoice_no",
    "StockCode": "stock_code", "Stock Code": "stock_code",
    "Description": "description", "Quantity": "quantity",
    "InvoiceDate": "invoice_date", "Invoice Date": "invoice_date",
    "UnitPrice": "unit_price", "Unit Price": "unit_price",
    "CustomerID": "customer_id", "Customer ID": "customer_id", "Country": "country",
}
REQUIRED_COLUMNS = ("invoice_no", "stock_code", "quantity", "invoice_date", "unit_price")
OUTPUT_COLUMNS = ["invoice_no", "stock_code", "description", "quantity", "invoice_date", "unit_price", "line_total", "customer_id", "country", "currency"]

@dataclass
class TransformResult:
    sales_lines: pd.DataFrame
    excluded_rows: pd.DataFrame
    report: dict[str, Any]


def _normalize_identifier(value: Any) -> Any:
    """Normalize Excel numeric IDs such as 17850.0 without damaging string IDs."""
    if pd.isna(value):
        return pd.NA
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value).strip()
    value = str(value).strip()
    return value if value else pd.NA


def _normalize_columns(source: pd.DataFrame) -> pd.DataFrame:
    frame = source.copy()
    frame = frame.rename(columns={c: COLUMN_ALIASES.get(str(c).strip(), str(c).strip()) for c in frame.columns})
    if frame.columns.duplicated().any():
        duplicates = frame.columns[frame.columns.duplicated()].tolist()
        raise ValueError(f"Duplicate columns after normalization: {duplicates}")
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError("The source file is missing required UCI Online Retail columns: " + ", ".join(missing))
    for optional in ("description", "customer_id", "country"):
        if optional not in frame.columns:
            frame[optional] = pd.NA
    return frame


def transform_online_retail(source: pd.DataFrame) -> TransformResult:
    """Return validated positive sale lines, excluded rows, and quality metrics.

    Cancellation invoices and negative quantities are excluded from ordinary
    sales, but retained in the exclusion output. Missing customer IDs remain
    usable for aggregate and basket analysis. Zero prices are allowed. Duplicate
    invoice/product pairs are flagged rather than silently dropped.
    """
    if source.empty:
        raise ValueError("The source dataset contains no rows.")
    frame = _normalize_columns(source)
    frame["_source_row"] = range(2, len(frame) + 2)  # source XLSX header is row 1
    for col in ("invoice_no", "stock_code", "description", "customer_id", "country"):
        frame[col] = frame[col].map(_normalize_identifier).astype("string").str.strip()
    frame["quantity"] = pd.to_numeric(frame["quantity"], errors="coerce")
    frame["unit_price"] = pd.to_numeric(frame["unit_price"], errors="coerce")
    frame["invoice_date"] = pd.to_datetime(frame["invoice_date"], errors="coerce")
    # UCI timestamps are naive. Do not falsely label them UTC.
    frame["invoice_date"] = frame["invoice_date"].dt.tz_localize(None)
    for col in ("description", "customer_id", "country"):
        frame[col] = frame[col].replace("", pd.NA)

    reasons = pd.Series("", index=frame.index, dtype="string")
    invoice_text = frame["invoice_no"].fillna("")
    cancellation = invoice_text.str.upper().str.startswith("C")
    returns = frame["quantity"].lt(0) & ~cancellation
    reasons.loc[cancellation] = "cancellation_invoice"
    reasons.loc[returns] = "return_or_negative_quantity"
    invalid_required = (
        frame["invoice_no"].isna() | frame["invoice_no"].eq("") |
        frame["stock_code"].isna() | frame["stock_code"].eq("") |
        frame["quantity"].isna() | frame["invoice_date"].isna() | frame["unit_price"].isna()
    )
    reasons.loc[(reasons == "") & invalid_required] = "missing_or_invalid_required_field"
    non_integer = frame["quantity"].notna() & (frame["quantity"] % 1 != 0) & (reasons == "")
    reasons.loc[non_integer] = "non_integer_quantity"
    zero_quantity = frame["quantity"].eq(0) & (reasons == "")
    reasons.loc[zero_quantity] = "zero_quantity"
    negative_price = frame["unit_price"].lt(0) & (reasons == "")
    reasons.loc[negative_price] = "negative_unit_price"

    excluded_mask = reasons.ne("")
    excluded = frame.loc[excluded_mask].copy()
    excluded["exclusion_reason"] = reasons.loc[excluded_mask]
    accepted = frame.loc[~excluded_mask].copy()
    accepted["quantity"] = accepted["quantity"].astype("int64")
    accepted["unit_price"] = accepted["unit_price"].astype("float64")
    missing_desc = accepted["description"].isna()
    missing_description_count = int(missing_desc.sum())
    accepted.loc[missing_desc, "description"] = (
        "Unknown product (StockCode: " + accepted.loc[missing_desc, "stock_code"].astype(str) + ")"
    )
    accepted["line_total"] = accepted["quantity"] * accepted["unit_price"]
    accepted["currency"] = "GBP"

    duplicate_mask = accepted.duplicated(subset=["invoice_no", "stock_code"], keep=False)
    duplicate_pair_rows = int(duplicate_mask.sum())
    duplicate_pair_count = int(accepted.loc[duplicate_mask, ["invoice_no", "stock_code"]].drop_duplicates().shape[0])
    product_counts = accepted.groupby("invoice_no")["stock_code"].nunique()
    report: dict[str, Any] = {
        "dataset": "UCI Online Retail", "currency": "GBP",
        "source_rows": int(len(frame)), "accepted_sales_lines": int(len(accepted)),
        "excluded_rows": int(len(excluded)),
        "exclusion_counts": {str(k): int(v) for k, v in excluded["exclusion_reason"].value_counts().items()},
        "missing_customer_id_rows_accepted": int(accepted["customer_id"].isna().sum()),
        "missing_description_rows_with_fallback": missing_description_count,
        "duplicate_invoice_product_pair_count": duplicate_pair_count,
        "rows_in_duplicate_invoice_product_pairs": duplicate_pair_rows,
        "distinct_invoices": int(accepted["invoice_no"].nunique()),
        "distinct_products": int(accepted["stock_code"].nunique()),
        "distinct_identified_customers": int(accepted["customer_id"].nunique()),
        "invoices_with_multiple_distinct_products": int((product_counts >= 2).sum()),
        "first_invoice_date": accepted["invoice_date"].min().isoformat() if not accepted.empty else None,
        "last_invoice_date": accepted["invoice_date"].max().isoformat() if not accepted.empty else None,
        "notes": [
            "Only positive-quantity non-cancellation rows are included in sales_lines.",
            "Cancellation and return rows remain in excluded_rows for audit.",
            "Missing customer IDs are not imputed and remain available for aggregate/basket analysis.",
            "Inventory and product cost are not inferred from this historical dataset.",
            "InvoiceDate is preserved as a naive source timestamp; no timezone was invented.",
            "Duplicate invoice/product rows are flagged, not silently removed.",
        ],
    }
    accepted = accepted[OUTPUT_COLUMNS].sort_values(["invoice_date", "invoice_no", "stock_code"], kind="stable").reset_index(drop=True)
    excluded = excluded.sort_values("_source_row", kind="stable").reset_index(drop=True)
    return TransformResult(accepted, excluded, report)
