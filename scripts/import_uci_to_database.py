"""Import processed UCI Online Retail lines into a separate GBP demo store.

The importer is deliberately opt-in and transactional. It never alters or
merges into another store. It creates no inventory rows because the dataset
contains no current stock snapshot. Existing completed imports are a no-op;
partial pre-existing imports are rejected for manual investigation.
"""
from __future__ import annotations

import argparse
import sys
import uuid
from datetime import timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import func, select, insert
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database.connection import get_engine
from app.database.models import Store, Product, Customer, Sale, SaleItem

STORE_NAME = "UCI Online Retail Demo"
BATCH_SIZE = 5000


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data" / "processed" / "sales_lines.csv")
    parser.add_argument("--confirm-import", action="store_true", help="Required to write data to PostgreSQL.")
    return parser.parse_args()


def to_utc(value):
    ts = pd.Timestamp(value)
    if pd.isna(ts):
        raise ValueError("A sale line has an invalid invoice_date.")
    # UCI timestamps are UK local wall-clock values without an explicit zone.
    return ts.to_pydatetime().replace(tzinfo=ZoneInfo("Europe/London")).astimezone(timezone.utc)


def main() -> int:
    args = parse_args()
    if not args.input.is_file():
        print(f"ERROR: processed CSV not found: {args.input}", file=sys.stderr)
        return 2
    if not args.confirm_import:
        print("Dry run only. Review the source and rerun with --confirm-import to write to PostgreSQL.")
        df = pd.read_csv(args.input, dtype={"invoice_no": str, "stock_code": str, "customer_id": str})
        print(f"Rows={len(df):,}; invoices={df['invoice_no'].nunique():,}; products={df['stock_code'].nunique():,}; customers={df['customer_id'].nunique():,}")
        print("No database rows were modified.")
        return 0

    df = pd.read_csv(args.input, dtype={"invoice_no": str, "stock_code": str, "customer_id": str})
    required = {"invoice_no", "stock_code", "description", "quantity", "invoice_date", "unit_price", "line_total", "customer_id"}
    missing = sorted(required - set(df.columns))
    if missing:
        print("ERROR: processed CSV missing columns: " + ", ".join(missing), file=sys.stderr)
        return 2
    if df.empty:
        print("ERROR: processed CSV is empty.", file=sys.stderr)
        return 2
    if df["invoice_no"].isna().any() or df["stock_code"].isna().any():
        print("ERROR: invoice_no or stock_code contains missing values.", file=sys.stderr)
        return 2
    if (pd.to_numeric(df["quantity"], errors="coerce") <= 0).any() or (pd.to_numeric(df["unit_price"], errors="coerce") < 0).any():
        print("ERROR: invalid quantity or unit price in processed CSV.", file=sys.stderr)
        return 2

    df["quantity"] = pd.to_numeric(df["quantity"], errors="raise").astype(int)
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="raise")
    df["line_total"] = pd.to_numeric(df["line_total"], errors="raise")
    df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="raise")

    # A repeated run cannot duplicate transactions. An existing store with any
    # records is refused rather than guessed to be a complete/partial import.
    engine = get_engine()
    with Session(engine) as session:
        existing = session.execute(select(Store).where(Store.name == STORE_NAME)).scalar_one_or_none()
        if existing is not None:
            sale_count = session.scalar(select(func.count()).select_from(Sale).where(Sale.store_id == existing.id)) or 0
            product_count = session.scalar(select(func.count()).select_from(Product).where(Product.store_id == existing.id)) or 0
            customer_count = session.scalar(select(func.count()).select_from(Customer).where(Customer.store_id == existing.id)) or 0
            if sale_count and product_count:
                print(f"UCI demo store already contains {sale_count:,} sales, {product_count:,} products, and {customer_count:,} customers. Import skipped; no changes made.")
                return 0
            print("ERROR: a UCI demo store exists but appears incomplete. Import stopped to avoid duplicating or mixing records.", file=sys.stderr)
            return 3

    # Build normalized maps in memory. Stable prefixed keys keep this dataset
    # isolated from the live store and prevent accidental SKU/invoice overlap.
    product_groups = df.sort_values("invoice_date", kind="stable").groupby("stock_code", sort=False)
    products_data = []
    for code, group in product_groups:
        description = next((str(x).strip() for x in group["description"] if pd.notna(x) and str(x).strip()), f"Unknown product ({code})")
        products_data.append({"source_code": str(code), "name": description, "selling_price": Decimal(str(float(group.iloc[-1]["unit_price"]))), "cost_price": Decimal("0"), "reorder_level": 0, "is_active": True})

    customer_ids = sorted(set(df["customer_id"].dropna().astype(str).str.strip()) - {"", "nan", "<NA>"})
    invoice_groups = df.groupby("invoice_no", sort=False)
    invoice_info = []
    customer_source_to_id = {source_id: uuid.uuid4() for source_id in customer_ids}
    sale_source_to_id = {}
    for invoice, group in invoice_groups:
        invoice = str(invoice).strip()
        if not invoice or invoice.upper().startswith("C"):
            raise ValueError(f"Unexpected cancellation invoice in processed data: {invoice}")
        cust = group["customer_id"].dropna().astype(str).str.strip()
        cust = cust[~cust.isin(["", "nan", "<NA>"])]
        # Invoice should map to one customer. If source conflicts, fail rather
        # than attach sales to an arbitrary customer.
        distinct_customers = cust.unique()
        if len(distinct_customers) > 1:
            raise ValueError(f"Invoice {invoice} maps to multiple customer IDs.")
        source_customer = distinct_customers[0] if len(distinct_customers) else None
        sale_id = uuid.uuid4()
        sale_source_to_id[invoice] = sale_id
        total = sum((Decimal(str(x)) for x in group["line_total"]), Decimal("0"))
        if total < 0:
            raise ValueError(f"Invoice {invoice} has a negative total.")
        invoice_info.append({"id": sale_id, "source_invoice": invoice, "customer_id": customer_source_to_id.get(source_customer), "sold_at": to_utc(group["invoice_date"].min()), "total": total})

    product_source_to_id = {p["source_code"]: uuid.uuid4() for p in products_data}
    try:
        with engine.begin() as conn:
            store_id = uuid.uuid4()
            conn.execute(insert(Store.__table__), [{"id": store_id, "name": STORE_NAME, "currency": "GBP"}])
            conn.execute(insert(Product.__table__), [
                {"id": product_source_to_id[p["source_code"]], "store_id": store_id, "category_id": None,
                 "sku": f"UCI-{p['source_code']}", "name": p["name"], "description": "UCI Online Retail historical product; current cost and stock are unknown.",
                 "selling_price": p["selling_price"], "cost_price": p["cost_price"], "reorder_level": p["reorder_level"], "is_active": True}
                for p in products_data
            ])
            conn.execute(insert(Customer.__table__), [
                {"id": customer_source_to_id[cid], "store_id": store_id, "name": f"UCI Customer {cid}", "email": None, "phone": None}
                for cid in customer_ids
            ])
            conn.execute(insert(Sale.__table__), [
                {"id": info["id"], "store_id": store_id, "customer_id": info["customer_id"], "sale_number": f"UCI-{info['source_invoice']}",
                 "status": "completed", "sold_at": info["sold_at"], "subtotal": info["total"], "discount": Decimal("0"), "total_amount": info["total"]}
                for info in invoice_info
            ])
            product_id_col = df["stock_code"].astype(str).map(product_source_to_id)
            sale_id_col = df["invoice_no"].astype(str).map(sale_source_to_id)
            for start in range(0, len(df), BATCH_SIZE):
                chunk = df.iloc[start:start + BATCH_SIZE]
                rows = []
                for idx, row in chunk.iterrows():
                    rows.append({"id": uuid.uuid4(), "sale_id": sale_id_col.loc[idx], "store_id": store_id,
                                 "product_id": product_id_col.loc[idx], "quantity": int(row["quantity"]),
                                 "unit_price": Decimal(str(float(row["unit_price"]))), "line_total": Decimal(str(float(row["line_total"])))})
                conn.execute(insert(SaleItem.__table__), rows)
        print("UCI Online Retail imported successfully into a separate GBP demo store.")
        print(f"Store: {STORE_NAME}")
        print(f"Products: {len(products_data):,}; customers: {len(customer_ids):,}; invoices: {len(invoice_info):,}; sale lines: {len(df):,}")
        print("No inventory rows were created because the source contains no current stock snapshot.")
        return 0
    except Exception as exc:
        print(f"ERROR: import failed and transaction was rolled back ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
