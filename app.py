import streamlit as st
import pandas as pd
from sqlalchemy import text

from app.database.connection import get_engine
from app.utils.ui import page_header, metric_card, module_button


st.set_page_config(
    page_title="Smart Retail",
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


# ==========================================================
# HEADER
# ==========================================================

page_header(
    "Smart Retail",
    "Sales Management & Inventory Intelligence",
)


# ==========================================================
# BUSINESS OVERVIEW
# ==========================================================

st.subheader("Business Overview")

overview = query_df(
    """
    SELECT
        COALESCE(
            (SELECT SUM(quantity_on_hand)
             FROM public.inventory),
            0
        ) AS inventory_units,

        COALESCE(
            (SELECT SUM(total_amount)
             FROM public.sales
             WHERE status = 'completed'),
            0
        ) AS revenue,

        COALESCE(
            (SELECT COUNT(*)
             FROM public.sales
             WHERE status = 'completed'),
            0
        ) AS transactions,

        COALESCE(
            (SELECT COUNT(*)
             FROM public.products
             WHERE is_active = TRUE),
            0
        ) AS products
    """
).iloc[0]


low_stock = query_df(
    """
    SELECT COUNT(*) AS count
    FROM public.inventory i
    JOIN public.products p
        ON p.id = i.product_id
    WHERE i.quantity_on_hand <= p.reorder_level
    """
).iloc[0]["count"]


c1, c2, c3 = st.columns(3)

with c1:
    metric_card(
        "📦 Inventory Level",
        f"{int(overview['inventory_units']):,}",
        f"⚠ {int(low_stock)} items below reorder",
    )

with c2:
    metric_card(
        "🛒 Total Sales",
        int(overview["transactions"]),
        "Completed transactions",
    )

with c3:
    metric_card(
        "💰 Revenue",
        f"₹{float(overview['revenue']):,.0f}",
        "Current database total",
    )


st.divider()


# ==========================================================
# QUICK ACCESS
# ==========================================================

st.subheader("Quick Access")

row1 = st.columns(3)

with row1[0]:
    module_button(
        "Sales Management",
        "🛒",
        "pages/sales.py",
    )

with row1[1]:
    module_button(
        "Inventory Management",
        "📦",
        "pages/inventory.py",
    )

with row1[2]:
    module_button(
        "Analytics Dashboard",
        "📊",
        "pages/analytics.py",
    )


row2 = st.columns(3)

with row2[0]:
    module_button(
        "Market Basket Analysis",
        "🧺",
        "pages/market_basket.py",
    )

with row2[1]:
    module_button(
        "Customers & Segments",
        "👥",
        "pages/Customers_and_Segments.py",
    )

with row2[2]:
    module_button(
        "Demand Forecast",
        "📈",
        "pages/Demand_Forecast.py",
    )


st.divider()


# ==========================================================
# LOW STOCK PREVIEW
# ==========================================================

st.subheader("⚠️ Inventory Alerts")

alerts = query_df(
    """
    SELECT
        p.name AS product,
        i.quantity_on_hand AS stock,
        p.reorder_level AS reorder_level
    FROM public.inventory i
    JOIN public.products p
        ON p.id = i.product_id
    WHERE i.quantity_on_hand <= p.reorder_level
    ORDER BY i.quantity_on_hand ASC
    """
)

if alerts.empty:
    st.success("All products are above their reorder levels.")

else:
    st.warning(
        f"{len(alerts)} product(s) require attention."
    )

    st.dataframe(
        alerts,
        use_container_width=True,
        hide_index=True,
    )