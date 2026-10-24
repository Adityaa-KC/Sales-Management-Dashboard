import pandas as pd
import pytest
from app.analytics.market_basket import run_market_basket_analysis


def sample_lines():
    return pd.DataFrame([
        {"invoice_no":"I1", "stock_code":"A", "description":"Apple", "quantity":1},
        {"invoice_no":"I1", "stock_code":"B", "description":"Bread", "quantity":1},
        {"invoice_no":"I2", "stock_code":"A", "description":"Apple", "quantity":1},
        {"invoice_no":"I2", "stock_code":"B", "description":"Bread", "quantity":2},
        {"invoice_no":"I3", "stock_code":"A", "description":"Apple", "quantity":1},
        {"invoice_no":"I3", "stock_code":"C", "description":"Coffee", "quantity":1},
        {"invoice_no":"I4", "stock_code":"A", "description":"Apple", "quantity":1},
    ])


def test_rules_are_calculated_from_invoice_baskets():
    pytest.importorskip("mlxtend")
    result = run_market_basket_analysis(sample_lines(), min_support=.25, min_confidence=.2, min_lift=0, max_len=2)
    assert result.summary["transactions"] == 4
    assert result.summary["transactions_with_multiple_products"] == 3
    assert result.summary["distinct_products"] == 3
    assert result.summary["rules_found"] > 0
    assert result.rules["support"].between(0, 1).all()
    assert result.rules["confidence"].between(0, 1).all()


def test_duplicate_product_within_invoice_counts_once():
    pytest.importorskip("mlxtend")
    data = pd.concat([sample_lines(), sample_lines().iloc[[0]]], ignore_index=True)
    result = run_market_basket_analysis(data, min_support=.25, min_confidence=.2, min_lift=0, max_len=2)
    assert result.summary["transactions"] == 4
    assert result.summary["valid_invoice_product_pairs"] == 7


def test_single_product_transactions_return_explanation_not_fake_rules():
    result = run_market_basket_analysis(pd.DataFrame([
        {"invoice_no":"I1", "stock_code":"A", "quantity":1},
        {"invoice_no":"I2", "stock_code":"A", "quantity":1},
    ]))
    assert result.summary["status"] == "insufficient_data"
    assert result.rules.empty
    assert result.summary["warning"]


def test_invalid_rows_are_counted_and_ignored():
    pytest.importorskip("mlxtend")
    data = pd.concat([sample_lines(), pd.DataFrame([
        {"invoice_no":None, "stock_code":"X", "quantity":1},
        {"invoice_no":"I5", "stock_code":"D", "quantity":-1},
    ])], ignore_index=True)
    result = run_market_basket_analysis(data, min_support=.25, min_confidence=.2, min_lift=0, max_len=2)
    assert result.summary["invalid_or_nonpositive_rows_ignored"] == 2


@pytest.mark.parametrize("kwargs", [
    {"min_support":0}, {"min_support":1.1}, {"min_confidence":-0.1},
    {"min_lift":-1}, {"max_len":1}, {"max_rules":0},
])
def test_invalid_parameters_raise(kwargs):
    with pytest.raises(ValueError):
        run_market_basket_analysis(sample_lines(), **kwargs)


def test_missing_required_columns_raise_clear_error():
    with pytest.raises(ValueError, match="Missing required columns"):
        run_market_basket_analysis(pd.DataFrame({"invoice_no":["I1"]}))
