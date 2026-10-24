"""
Read-only audit of SmartRetail data readiness for machine-learning modules.

Run from the project root:
    python scripts/audit_ml_readiness.py

This script does not insert, update, or delete application data.
It uses the project's existing Streamlit database secret configuration.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def get_read_only_engine():
    """Build an engine using existing config; never print credentials."""
    database_url = None

    # Preserve the project's existing configuration contract.
    try:
        database_url = st.secrets["database"]["url"]
    except (FileNotFoundError, KeyError, TypeError):
        pass

    # Allow a standard environment variable for running this diagnostic
    # outside Streamlit, without changing application configuration.
    import os
    database_url = database_url or os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "Database URL not found. Configure [database].url in "
            ".streamlit/secrets.toml or set DATABASE_URL in your shell."
        )

    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"sslmode": "require"},
        pool_size=1,
        max_overflow=0,
    )


QUERIES = {
    "stores": "SELECT COUNT(*) AS n FROM public.stores",
    "products": "SELECT COUNT(*) AS n FROM public.products",
    "active_products": "SELECT COUNT(*) AS n FROM public.products WHERE is_active IS TRUE",
    "customers": "SELECT COUNT(*) AS n FROM public.customers",
    "inventory_rows": "SELECT COUNT(*) AS n FROM public.inventory",
    "sales_all": "SELECT COUNT(*) AS n FROM public.sales",
    "sales_completed": "SELECT COUNT(*) AS n FROM public.sales WHERE status = 'completed'",
    "sales_voided": "SELECT COUNT(*) AS n FROM public.sales WHERE status = 'voided'",
    "sale_items": "SELECT COUNT(*) AS n FROM public.sale_items",
    "analysis_runs": "SELECT COUNT(*) AS n FROM public.analysis_runs",
}


def scalar(conn, sql: str) -> Any:
    return conn.execute(text(sql)).scalar_one()


def main() -> int:
    engine = None
    try:
        engine = get_read_only_engine()
        with engine.connect() as conn:
            # Validate connection and database dialect without exposing URL.
            dialect = conn.dialect.name
            print("SMARTRETAIL ML READINESS AUDIT")
            print("=" * 40)
            print(f"Database dialect: {dialect}")
            if dialect != "postgresql":
                print("WARNING: The project models use PostgreSQL-specific types; "
                      "verify this is the intended database.")

            print("\n1. TABLE COUNTS")
            for label, sql in QUERIES.items():
                try:
                    print(f"{label:20s}: {scalar(conn, sql)}")
                except SQLAlchemyError as exc:
                    print(f"{label:20s}: ERROR ({type(exc).__name__})")
                    print("  The table or expected column may be missing.")
                    return 2

            print("\n2. COMPLETED-SALE DATE COVERAGE")
            dates = conn.execute(text("""
                SELECT MIN(sold_at) AS first_sale,
                       MAX(sold_at) AS last_sale,
                       COUNT(DISTINCT DATE(sold_at)) AS distinct_sale_days
                FROM public.sales
                WHERE status = 'completed'
            """)).mappings().one()
            print(f"First completed sale : {dates['first_sale']}")
            print(f"Last completed sale  : {dates['last_sale']}")
            print(f"Distinct sale days   : {dates['distinct_sale_days']}")

            print("\n3. DATA QUALITY CHECKS")
            checks = [
                ("completed_sales_without_items", """
                    SELECT COUNT(*) FROM public.sales s
                    WHERE s.status = 'completed'
                      AND NOT EXISTS (
                        SELECT 1 FROM public.sale_items si WHERE si.sale_id = s.id
                      )
                """),
                ("sale_items_for_noncompleted_sales", """
                    SELECT COUNT(*) FROM public.sale_items si
                    JOIN public.sales s ON s.id = si.sale_id
                    WHERE s.status <> 'completed'
                """),
                ("sale_items_store_mismatch", """
                    SELECT COUNT(*) FROM public.sale_items si
                    JOIN public.sales s ON s.id = si.sale_id
                    WHERE si.store_id <> s.store_id
                """),
                ("sale_items_product_store_mismatch", """
                    SELECT COUNT(*) FROM public.sale_items si
                    JOIN public.products p ON p.id = si.product_id
                    WHERE si.store_id <> p.store_id
                """),
                ("duplicate_product_lines_per_sale", """
                    SELECT COUNT(*) FROM (
                        SELECT sale_id, product_id
                        FROM public.sale_items
                        GROUP BY sale_id, product_id
                        HAVING COUNT(*) > 1
                    ) d
                """),
                ("products_missing_inventory", """
                    SELECT COUNT(*) FROM public.products p
                    LEFT JOIN public.inventory i
                      ON i.product_id = p.id AND i.store_id = p.store_id
                    WHERE p.is_active IS TRUE AND i.product_id IS NULL
                """),
                ("sales_without_customer", """
                    SELECT COUNT(*) FROM public.sales
                    WHERE status = 'completed' AND customer_id IS NULL
                """),
                ("completed_sales_with_negative_total", """
                    SELECT COUNT(*) FROM public.sales
                    WHERE status = 'completed' AND total_amount < 0
                """),
            ]
            check_values = {}
            for label, sql in checks:
                value = scalar(conn, sql)
                check_values[label] = value
                print(f"{label:42s}: {value}")

            print("\n4. ML READINESS")
            completed_sales = scalar(
                conn, "SELECT COUNT(*) FROM public.sales WHERE status = 'completed'"
            )
            sale_items = scalar(conn, "SELECT COUNT(*) FROM public.sale_items")
            distinct_days = int(dates["distinct_sale_days"] or 0)
            customers_with_sales = scalar(conn, """
                SELECT COUNT(DISTINCT customer_id)
                FROM public.sales
                WHERE status = 'completed' AND customer_id IS NOT NULL
            """)
            transactions_with_multiple_products = scalar(conn, """
                SELECT COUNT(*) FROM (
                    SELECT s.id
                    FROM public.sales s
                    JOIN public.sale_items si ON si.sale_id = s.id
                    WHERE s.status = 'completed'
                    GROUP BY s.id
                    HAVING COUNT(DISTINCT si.product_id) >= 2
                ) t
            """)

            print(f"Market basket: completed sales={completed_sales}, "
                  f"items={sale_items}, multi-product transactions="
                  f"{transactions_with_multiple_products}")
            print(f"Segmentation: customers with completed sales={customers_with_sales}")
            print(f"Forecasting: distinct days with completed sales={distinct_days}")

            blockers = []
            if completed_sales == 0 or sale_items == 0:
                blockers.append("No usable completed-sale/item history.")
            if transactions_with_multiple_products == 0:
                blockers.append("Market basket analysis needs transactions containing "
                                "at least two distinct products.")
            if customers_with_sales < 2:
                blockers.append("Customer segmentation has too few customers with sales "
                                "for meaningful clustering.")
            if distinct_days < 30:
                blockers.append("Forecasting history is short (<30 distinct sale days); "
                                "forecast quality may be unreliable.")
            if any(v > 0 for k, v in check_values.items()
                   if k in {"completed_sales_without_items",
                            "sale_items_for_noncompleted_sales",
                            "sale_items_store_mismatch",
                            "sale_items_product_store_mismatch"}):
                blockers.append("Resolve transaction/item consistency errors before training.")

            print("\n5. INITIAL FINDINGS")
            if blockers:
                for item in blockers:
                    print(f"- REVIEW: {item}")
            else:
                print("- Basic volume checks passed. This does not prove data quality "
                      "or model suitability; validate chronology and business meaning next.")
            print("\nAudit complete. No application rows were modified.")
        return 0

    except (RuntimeError, SQLAlchemyError) as exc:
        print("\nAUDIT FAILED")
        print(f"{type(exc).__name__}: {exc}")
        print("Check database connectivity, credentials, SSL settings, and table migrations.")
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
