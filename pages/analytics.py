import streamlit as st
import pandas as pd
from sqlalchemy import text

from app.database.connection import get_engine
from app.utils.ui import page_header, metric_card


st.set_page_config(
    page_title="Analytics Dashboard",
    page_icon="📊",
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
    "📊 Analytics Dashboard",
    "Sales performance and business intelligence",
)


stats = query_df(
    """
    SELECT
        COALESCE(SUM(total_amount), 0) AS revenue,
        COUNT(*) AS sales,
        COUNT(DISTINCT customer_id) AS customers
    FROM public.sales
    WHERE status = 'completed'
    """
).iloc[0]


c1, c2, c3 = st.columns(3)

with c1:
    metric_card(
        "Revenue",
        f"₹{float(stats['revenue']):,.0f}",
        "Total completed sales",
    )

with c2:
    metric_card(
        "Sales",
        int(stats["sales"]),
        "Transactions",
    )

with c3:
    metric_card(
        "Customers",
        int(stats["customers"]),
        "Unique customers",
    )


st.divider()


# Revenue by product

st.subheader("Revenue by Product")

df = query_df(
    """
    SELECT
        p.name AS product,
        SUM(si.line_total) AS revenue
    FROM public.sale_items si
    JOIN public.products p
        ON p.id = si.product_id
    GROUP BY p.name
    ORDER BY revenue DESC
    """
)


if not df.empty:

    st.bar_chart(
        df.set_index("product")
    )


# Sales by date

st.subheader("Sales Trend")

trend = query_df(
    """
    SELECT
        DATE(sold_at) AS sale_date,
        SUM(total_amount) AS revenue
    FROM public.sales
    WHERE status = 'completed'
    GROUP BY DATE(sold_at)
    ORDER BY sale_date
    """
)


if not trend.empty:

    trend["sale_date"] = pd.to_datetime(
        trend["sale_date"]
    )

    st.line_chart(
        trend.set_index("sale_date")
    )


if st.button("← Back to Home"):
    st.switch_page("app.py")