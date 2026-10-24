"""Database-independent market basket analysis for SmartRetail."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import pandas as pd

REQUIRED_COLUMNS = {"invoice_no", "stock_code"}
RULE_COLUMNS = ["antecedents", "consequents", "support", "confidence", "lift", "leverage", "conviction"]

@dataclass
class MarketBasketResult:
    rules: pd.DataFrame
    summary: dict[str, Any]
    frequent_itemsets: pd.DataFrame


def _validate_parameters(min_support: float, min_confidence: float, min_lift: float,
                         max_len: int | None, max_rules: int) -> None:
    if not 0 < min_support <= 1:
        raise ValueError("min_support must be greater than 0 and at most 1.")
    if not 0 <= min_confidence <= 1:
        raise ValueError("min_confidence must be between 0 and 1.")
    if min_lift < 0:
        raise ValueError("min_lift must be non-negative.")
    if max_len is not None and max_len < 2:
        raise ValueError("max_len must be at least 2 when provided.")
    if max_rules < 1:
        raise ValueError("max_rules must be at least 1.")


def _prepare_lines(lines: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(lines, pd.DataFrame):
        raise TypeError("lines must be a pandas DataFrame.")
    if lines.empty:
        raise ValueError("No sales lines were provided.")
    missing = sorted(REQUIRED_COLUMNS - set(lines.columns))
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    frame = lines.copy()
    frame["invoice_no"] = frame["invoice_no"].astype("string").str.strip()
    frame["stock_code"] = frame["stock_code"].astype("string").str.strip()
    invalid = (frame["invoice_no"].isna() | frame["invoice_no"].eq("") |
               frame["stock_code"].isna() | frame["stock_code"].eq(""))
    invalid_count = int(invalid.sum())
    frame = frame.loc[~invalid].copy()
    if frame.empty:
        raise ValueError("No rows contain both a valid invoice_no and stock_code.")

    if "quantity" in frame.columns:
        quantity = pd.to_numeric(frame["quantity"], errors="coerce")
        bad_quantity = quantity.isna() | quantity.le(0)
        invalid_count += int(bad_quantity.sum())
        frame = frame.loc[~bad_quantity].copy()
    if frame.empty:
        raise ValueError("No valid positive-quantity sale lines remain.")

    if "description" in frame.columns:
        frame["description"] = frame["description"].astype("string").str.strip()
    else:
        frame["description"] = pd.NA
    # Product identity is the stock code, not the often-inconsistent description.
    frame = frame.drop_duplicates(subset=["invoice_no", "stock_code"])
    labels: dict[str, str] = {}
    for code, group in frame.groupby("stock_code", sort=False):
        descriptions = group["description"].dropna()
        descriptions = descriptions[descriptions.ne("")]
        name = str(descriptions.iloc[0]) if not descriptions.empty else f"Product {code}"
        labels[str(code)] = f"{name} [{code}]"
    return frame, {"invalid_or_nonpositive_rows_ignored": invalid_count, "product_labels": labels}


def _display_itemset(items: frozenset[str], labels: dict[str, str]) -> str:
    return " + ".join(sorted(labels.get(str(item), f"Product {item}") for item in items))


def run_market_basket_analysis(
    lines: pd.DataFrame, *, min_support: float = 0.01,
    min_confidence: float = 0.30, min_lift: float = 1.0,
    max_len: int | None = 3, max_rules: int = 100,
) -> MarketBasketResult:
    """Calculate Apriori frequent itemsets and association rules from invoice baskets.

    Support uses all valid invoices as the denominator, including one-item invoices.
    A product is counted once per invoice, even if duplicate source lines exist.
    """
    _validate_parameters(min_support, min_confidence, min_lift, max_len, max_rules)
    frame, metadata = _prepare_lines(lines)
    basket = (frame.assign(present=True).pivot_table(
        index="invoice_no", columns="stock_code", values="present",
        aggfunc="max", fill_value=False).astype(bool))
    transaction_count = int(basket.shape[0])
    multi_item_count = int((basket.sum(axis=1) >= 2).sum())
    summary: dict[str, Any] = {
        "transactions": transaction_count,
        "transactions_with_multiple_products": multi_item_count,
        "distinct_products": int(basket.shape[1]),
        "valid_invoice_product_pairs": int(len(frame)),
        "min_support": float(min_support), "min_confidence": float(min_confidence),
        "min_lift": float(min_lift), "max_len": max_len, "rules_found": 0,
        "status": "ready", "warning": None,
        "invalid_or_nonpositive_rows_ignored": metadata["invalid_or_nonpositive_rows_ignored"],
    }
    if transaction_count < 2 or multi_item_count == 0 or basket.shape[1] < 2:
        summary["status"] = "insufficient_data"
        summary["warning"] = "At least one invoice with two distinct products is required to generate association rules."
        return MarketBasketResult(pd.DataFrame(columns=RULE_COLUMNS), summary,
                                  pd.DataFrame(columns=["support", "itemsets"]))

    try:
        from mlxtend.frequent_patterns import apriori, association_rules
    except ImportError as exc:
        raise ImportError("Market basket analysis requires mlxtend. Install project dependencies with `python -m pip install -r requirements.txt`.") from exc

    sparse_basket = basket.astype(pd.SparseDtype(bool, fill_value=False))
    frequent = apriori(sparse_basket, min_support=min_support, use_colnames=True,
                       max_len=max_len, low_memory=True)
    if frequent.empty:
        summary["status"] = "no_frequent_itemsets"
        summary["warning"] = "No itemsets met min_support. Lower min_support carefully and rerun."
        return MarketBasketResult(pd.DataFrame(columns=RULE_COLUMNS), summary, frequent)

    frequent["itemsets"] = frequent["itemsets"].map(lambda items: frozenset(map(str, items)))
    try:
        rules = association_rules(frequent, metric="confidence", min_threshold=min_confidence)
    except TypeError:
        # Compatibility with mlxtend versions that require num_itemsets.
        rules = association_rules(frequent, num_itemsets=transaction_count,
                                  metric="confidence", min_threshold=min_confidence)
    if not rules.empty:
        rules = rules.loc[rules["lift"] >= min_lift].copy()
        rules["antecedents"] = rules["antecedents"].map(lambda x: _display_itemset(frozenset(map(str, x)), metadata["product_labels"]))
        rules["consequents"] = rules["consequents"].map(lambda x: _display_itemset(frozenset(map(str, x)), metadata["product_labels"]))
        rules = rules.sort_values(["lift", "confidence", "support"], ascending=[False, False, False], kind="stable")
        rules = rules[RULE_COLUMNS].head(max_rules).reset_index(drop=True)
    else:
        rules = pd.DataFrame(columns=RULE_COLUMNS)
    summary["rules_found"] = int(len(rules))
    if rules.empty:
        summary["status"] = "no_rules"
        summary["warning"] = "Frequent itemsets were found, but no rules met the confidence and lift thresholds."
    frequent_display = frequent.copy()
    frequent_display["itemsets"] = frequent_display["itemsets"].map(lambda x: _display_itemset(frozenset(map(str, x)), metadata["product_labels"]))
    return MarketBasketResult(rules, summary, frequent_display.reset_index(drop=True))


def load_sales_lines_csv(path: str) -> pd.DataFrame:
    """Read the processed sales CSV while preserving invoice and product IDs as strings."""
    return pd.read_csv(path, dtype={"invoice_no": "string", "stock_code": "string", "customer_id": "string"})
