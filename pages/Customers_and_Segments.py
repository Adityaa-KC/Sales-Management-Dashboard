import streamlit as st
import pandas as pd
from sqlalchemy import text

from app.database.connection import get_engine
from app.utils.ui import page_header, metric_card


st.set_page_config(
    page_title="Customers & Segments",
    page_icon="👥",
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
    "👥 Customers & Segments",
    "Understand customer purchasing behaviour",
)


stats = query_df(
    """
    SELECT
        COUNT(*) AS customers
    FROM public.customers
    """
).iloc[0]


revenue = query_df(
    """
    SELECT
        COALESCE(SUM(total_amount), 0) AS revenue
    FROM public.sales
    WHERE status = 'completed'
    """
).iloc[0]["revenue"]


c1, c2 = st.columns(2)

with c1:
    metric_card(
        "Customers",
        int(stats["customers"]),
        "Registered customers",
    )

with c2:
    metric_card(
        "Customer Revenue",
        f"₹{float(revenue):,.0f}",
        "Completed sales",
    )


st.divider()


customers = query_df(
    """
    SELECT
        c.name AS customer,
        COUNT(s.id) AS purchases,
        COALESCE(SUM(s.total_amount), 0) AS spending
    FROM public.customers c
    LEFT JOIN public.sales s
        ON s.customer_id = c.id
        AND s.status = 'completed'
    GROUP BY c.id, c.name
    ORDER BY spending DESC
    """
)


st.subheader("Customer Purchasing Behaviour")

st.dataframe(
    customers,
    use_container_width=True,
    hide_index=True,
)


st.info(
    "RFM-based customer segmentation can be applied to "
    "Recency, Frequency and Monetary purchasing behaviour."
)


if st.button("← Back to Home"):
    st.switch_page("app.py")