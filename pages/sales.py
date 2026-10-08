import streamlit as st
import pandas as pd
from sqlalchemy import text

from app.database.connection import get_engine
from app.utils.ui import page_header, metric_card


st.set_page_config(
    page_title="Sales Management",
    page_icon="🛒",
    layout="wide",
)


@st.cache_resource
def get_db():
    return get_engine()


engine = get_db()


def query_df(query):
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


page_header(
    "🛒 Sales Management",
    "Monitor sales performance and recent transactions",
)


# ==========================================================
# KPI
# ==========================================================

stats = query_df(
    """
    SELECT
        COALESCE(SUM(total_amount), 0) AS revenue,
        COUNT(*) AS transactions,
        COALESCE(AVG(total_amount), 0) AS average_bill
    FROM public.sales
    WHERE status = 'completed'
    """
).iloc[0]


c1, c2, c3 = st.columns(3)

with c1:
    metric_card(
        "Today's Sales",
        f"₹{float(stats['revenue']):,.0f}",
        "Completed sales",
    )

with c2:
    metric_card(
        "Transactions",
        int(stats["transactions"]),
        "Completed transactions",
    )

with c3:
    metric_card(
        "Average Bill",
        f"₹{float(stats['average_bill']):,.2f}",
        "Average transaction value",
    )


st.divider()


# ==========================================================
# TOP PRODUCTS
# ==========================================================

st.subheader("🏆 Top Selling Products")

products = query_df(
    """
    SELECT
        p.name AS product,
        SUM(si.quantity) AS units_sold,
        SUM(si.line_total) AS revenue
    FROM public.sale_items si
    JOIN public.products p
        ON p.id = si.product_id
    GROUP BY p.name
    ORDER BY revenue DESC
    LIMIT 10
    """
)


if not products.empty:

    col1, col2 = st.columns([1, 2])

    with col1:
        st.success(
            f"🏆 {products.iloc[0]['product']}"
        )

    with col2:
        st.bar_chart(
            products.set_index("product")["revenue"]
        )


st.divider()


# ==========================================================
# RECENT TRANSACTIONS
# ==========================================================

st.subheader("Recent Transactions")

transactions = query_df(
    """
    SELECT
        sale_number AS transaction,
        COALESCE(c.name, 'Walk-in Customer') AS customer,
        sold_at AS date,
        total_amount AS amount
    FROM public.sales s
    LEFT JOIN public.customers c
        ON c.id = s.customer_id
    WHERE s.status = 'completed'
    ORDER BY sold_at DESC
    LIMIT 10
    """
)


st.dataframe(
    transactions,
    use_container_width=True,
    hide_index=True,
)


if st.button("← Back to Home"):
    st.switch_page("app.py")