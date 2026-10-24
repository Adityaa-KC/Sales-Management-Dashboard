import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.data.transformer import transform_online_retail


def sample_data():
    return pd.DataFrame([
        {"InvoiceNo": "10001", "StockCode": "00123", "Description": " Product A ", "Quantity": 2, "InvoiceDate": "2011-01-01 10:00:00", "UnitPrice": 3.5, "CustomerID": 17850.0, "Country": "United Kingdom"},
        {"InvoiceNo": "10001", "StockCode": "B2", "Description": "Product B", "Quantity": 1, "InvoiceDate": "2011-01-01 10:00:00", "UnitPrice": 0, "CustomerID": 17850.0, "Country": "United Kingdom"},
        {"InvoiceNo": "C10002", "StockCode": "A1", "Description": "Cancelled", "Quantity": 1, "InvoiceDate": "2011-01-02 10:00:00", "UnitPrice": 4, "CustomerID": 17850, "Country": "United Kingdom"},
        {"InvoiceNo": "10003", "StockCode": "A1", "Description": "Return", "Quantity": -1, "InvoiceDate": "2011-01-03 10:00:00", "UnitPrice": 4, "CustomerID": None, "Country": "United Kingdom"},
        {"InvoiceNo": "10004", "StockCode": "A1", "Description": None, "Quantity": 3, "InvoiceDate": "2011-01-04 10:00:00", "UnitPrice": 2, "CustomerID": None, "Country": "United Kingdom"},
        {"InvoiceNo": "10005", "StockCode": "A1", "Description": "Bad price", "Quantity": 1, "InvoiceDate": "2011-01-05 10:00:00", "UnitPrice": -1, "CustomerID": 1, "Country": "United Kingdom"},
    ])


def test_separates_cancellations_returns_and_invalid_prices():
    result = transform_online_retail(sample_data())
    assert len(result.sales_lines) == 3
    assert len(result.excluded_rows) == 3
    assert set(result.excluded_rows["exclusion_reason"]) == {"cancellation_invoice", "return_or_negative_quantity", "negative_unit_price"}


def test_normalizes_values_and_preserves_zero_price():
    result = transform_online_retail(sample_data())
    lines = result.sales_lines.set_index("stock_code")
    assert lines.loc["00123", "customer_id"] == "17850"
    assert lines.loc["B2", "unit_price"] == 0
    assert lines.loc["00123", "line_total"] == 7
    assert lines.loc["A1", "description"] == "Unknown product (StockCode: A1)"
    assert pd.isna(lines.loc["A1", "customer_id"])
    assert set(result.sales_lines["currency"]) == {"GBP"}


def test_report_identifies_multi_product_invoice_and_missing_customer():
    result = transform_online_retail(sample_data())
    assert result.report["invoices_with_multiple_distinct_products"] == 1
    assert result.report["missing_customer_id_rows_accepted"] == 1
    assert result.report["distinct_invoices"] == 2


def test_missing_required_columns_fail_with_clear_message():
    with pytest.raises(ValueError, match="missing required"):
        transform_online_retail(pd.DataFrame({"InvoiceNo": ["1"]}))


def test_empty_dataset_is_rejected():
    with pytest.raises(ValueError, match="contains no rows"):
        transform_online_retail(pd.DataFrame())
