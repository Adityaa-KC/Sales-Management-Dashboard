"""Streamlit page for SmartRetail market basket analysis."""
from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

# Keep the page runnable with `streamlit run app.py` from the project root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.analytics.market_basket import run_market_basket_analysis
from app.utils.ui import page_header, metric_card
from app.utils.store_context import render_store_selector, query_df

st.set_page_config(
    page_title="Market Basket Analysis",
    page_icon="🧺",
    layout="wide",
)

store = render_store_selector()
if store is None:
    st.stop()
store_id, store_name, currency = store

page_header(
    "🧺 Market Basket Analysis",
    "Discover products frequently purchased together",
)
st.caption(f"Active store: {store_name} · Currency: {currency} · Data source: PostgreSQL")



@st.cache_data(show_spinner=False, ttl=60)
def load_store_sales(store_id: str) -> pd.DataFrame:
    """Read transaction lines from PostgreSQL for the selected store only."""
    return query_df("""
        SELECT s.sale_number AS invoice_no, p.sku AS stock_code,
               p.name AS description, si.quantity
        FROM public.sales s
        JOIN public.sale_items si ON si.sale_id = s.id AND si.store_id = s.store_id
        JOIN public.products p ON p.id = si.product_id AND p.store_id = si.store_id
        WHERE s.store_id = CAST(:store_id AS UUID)
          AND s.status = 'completed'
        ORDER BY s.sold_at, s.sale_number
    """, {"store_id": store_id})


def format_metric(value: float | int | None, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:.{digits}f}" if isinstance(value, float) else f"{value:,}"

try:
    sales_lines = load_store_sales(store_id)
except Exception as exc:
    st.error(f"Could not load transaction lines from PostgreSQL: {exc}")
    st.stop()

if sales_lines.empty:
    st.warning("This store has no completed sales with sale items. Import historical data or record transactions before running market basket analysis.")
    if st.button("← Back to Home"):
        st.switch_page("app.py")
    st.stop()

if store_name == "UCI Online Retail Demo":
    st.info("**Dataset mode: UCI Online Retail demonstration data (GBP).** Findings describe the historical UCI retailer. This page reads PostgreSQL and does not write to the database.")
else:
    st.info("**Dataset mode: selected store.** Results are calculated from completed sale items stored in PostgreSQL for this store.")

with st.expander("Analysis settings", expanded=True):
    with st.form("market_basket_settings"):
        left, middle, right, final = st.columns(4)
        with left:
            min_support = st.slider(
                "Minimum support", min_value=0.001, max_value=0.10,
                value=0.01, step=0.001,
                help="Minimum fraction of all invoices containing an itemset.",
            )
        with middle:
            min_confidence = st.slider(
                "Minimum confidence", min_value=0.05, max_value=1.0,
                value=0.30, step=0.05,
                help="Minimum probability of the consequent when the antecedent occurs.",
            )
        with right:
            min_lift = st.slider(
                "Minimum lift", min_value=0.0, max_value=10.0,
                value=1.0, step=0.25,
                help="Lift above 1 indicates a positive association versus independence.",
            )
        with final:
            max_len = st.selectbox(
                "Maximum products per itemset", options=[2, 3, 4], index=1,
                help="Larger itemsets can increase computation time substantially.",
            )
        max_rules = st.select_slider(
            "Maximum rules to display", options=[25, 50, 100, 250], value=100
        )
        run_analysis = st.form_submit_button("Run market basket analysis", type="primary")

if st.session_state.get("market_basket_store_id") != store_id:
    st.session_state.market_basket_result = None
    st.session_state.market_basket_store_id = store_id
if "market_basket_result" not in st.session_state:
    st.session_state.market_basket_result = None
if run_analysis:
    try:
        with st.spinner("Mining frequent itemsets and calculating association rules..."):
            result = run_market_basket_analysis(
                sales_lines,
                min_support=float(min_support),
                min_confidence=float(min_confidence),
                min_lift=float(min_lift),
                max_len=int(max_len),
                max_rules=int(max_rules),
            )
        st.session_state.market_basket_result = result
        st.session_state.market_basket_parameters = {
            "min_support": min_support,
            "min_confidence": min_confidence,
            "min_lift": min_lift,
            "max_len": max_len,
            "max_rules": max_rules,
        }
    except (ValueError, ImportError, MemoryError) as exc:
        st.error(f"Analysis could not be completed: {exc}")
    except Exception as exc:
        st.error(f"Unexpected analysis error ({type(exc).__name__}): {exc}")

result = st.session_state.market_basket_result

if result is None:
    st.subheader("Dataset overview")
    preview = sales_lines
    required = {"invoice_no", "stock_code"}
    if required.issubset(preview.columns):
        invoices = int(preview["invoice_no"].nunique())
        products = int(preview["stock_code"].nunique())
        pairs = int(preview[["invoice_no", "stock_code"]].drop_duplicates().shape[0])
        a, b, c = st.columns(3)
        with a:
            metric_card("Transactions", f"{invoices:,}", "Distinct invoice numbers")
        with b:
            metric_card("Products", f"{products:,}", "Distinct product codes")
        with c:
            metric_card("Invoice-product pairs", f"{pairs:,}", "Before rule mining")
    st.caption("Choose the thresholds above and run the analysis to generate rules.")
else:
    summary = result.summary
    rules = result.rules
    st.divider()
    if summary.get("status") == "insufficient_data":
        st.warning(summary.get("warning") or "Not enough transaction data to mine rules.")
    elif summary.get("status") == "no_frequent_itemsets":
        st.warning(summary.get("warning") or "No frequent itemsets met the support threshold.")
    elif summary.get("status") == "no_rules":
        st.warning(summary.get("warning") or "No rules met the selected thresholds.")
    else:
        st.success("Analysis completed. Metrics below were calculated from the selected dataset.")

    top_rule = rules.iloc[0] if not rules.empty else None
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Association Rules", f"{summary['rules_found']:,}", f"Limit: {summary['max_len']} products per itemset")
    with c2:
        metric_card("Transactions", f"{summary['transactions']:,}", "All valid invoices")
    with c3:
        metric_card("Multi-product Baskets", f"{summary['transactions_with_multiple_products']:,}", "At least 2 distinct products")
    with c4:
        metric_card("Distinct Products", f"{summary['distinct_products']:,}", "Product codes")

    if top_rule is not None:
        st.subheader("Top-ranked association")
        left, right = st.columns([3, 2])
        with left:
            st.markdown(f"**If a basket contains:** {top_rule['antecedents']}")
            st.markdown(f"**It is associated with:** {top_rule['consequents']}")
            st.caption("This is an association, not evidence of causation or a guaranteed recommendation.")
        with right:
            m1, m2, m3 = st.columns(3)
            m1.metric("Support", f"{top_rule['support']:.2%}")
            m2.metric("Confidence", f"{top_rule['confidence']:.2%}")
            m3.metric("Lift", f"{top_rule['lift']:.2f}×")

        st.subheader("Association rules")
        display_rules = rules.copy()
        for column in ("support", "confidence"):
            if column in display_rules:
                display_rules[column] = display_rules[column].map(lambda x: f"{x:.2%}")
        for column in ("lift", "leverage", "conviction"):
            if column in display_rules:
                display_rules[column] = display_rules[column].map(
                    lambda x: "∞" if pd.isna(x) or x == float("inf") else f"{x:.4f}"
                )
        st.dataframe(display_rules, use_container_width=True, hide_index=True)
        st.download_button(
            "Download rules as CSV",
            data=rules.to_csv(index=False).encode("utf-8"),
            file_name="smartretail_market_basket_rules.csv",
            mime="text/csv",
        )

        if "lift" in rules.columns:
            chart_data = rules.head(15).copy()
            chart_data["rule"] = chart_data["antecedents"] + " → " + chart_data["consequents"]
            st.subheader("Top rules by lift")
            st.bar_chart(chart_data.set_index("rule")["lift"], horizontal=True)
    else:
        st.info("No association rules are available with the current thresholds. Try lowering minimum support or confidence carefully.")

    with st.expander("Run diagnostics"):
        st.json(summary)
        if not result.frequent_itemsets.empty:
            st.write("Frequent itemsets meeting the support threshold")
            st.dataframe(result.frequent_itemsets.head(100), use_container_width=True, hide_index=True)

st.divider()
if st.button("← Back to Home"):
    st.switch_page("app.py")
