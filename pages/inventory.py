import streamlit as st
import pandas as pd
from sqlalchemy import text

from app.database.connection import get_engine
from app.utils.ui import page_header, metric_card


st.set_page_config(
    page_title="Inventory Management",
    page_icon="📦",
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
    "📦 Inventory Management",
    "Monitor stock levels and reorder requirements",
)


stats = query_df(
    """
    SELECT
        COALESCE(SUM(quantity_on_hand), 0) AS total_stock,
        COUNT(*) AS products,
        COUNT(*) FILTER (
            WHERE quantity_on_hand <= 0
        ) AS out_of_stock,
        COUNT(*) FILTER (
            WHERE quantity_on_hand <= reorder_level
        ) AS low_stock
    FROM public.inventory i
    JOIN public.products p
        ON p.id = i.product_id
    """
).iloc[0]


c1, c2, c3, c4 = st.columns(4)

with c1:
    metric_card(
        "📦 Inventory",
        f"{int(stats['total_stock']):,}",
        "Total units",
    )

with c2:
    metric_card(
        "Products",
        int(stats["products"]),
        "Tracked products",
    )

with c3:
    metric_card(
        "⚠ Low Stock",
        int(stats["low_stock"]),
        "Needs attention",
    )

with c4:
    metric_card(
        "🚫 Out of Stock",
        int(stats["out_of_stock"]),
        "Unavailable",
    )


st.divider()


inventory = query_df(
    """
    SELECT
        p.sku,
        p.name AS product,
        i.quantity_on_hand AS stock,
        p.reorder_level,
        CASE
            WHEN i.quantity_on_hand <= 0
                THEN 'OUT OF STOCK'
            WHEN i.quantity_on_hand <= p.reorder_level
                THEN 'LOW STOCK'
            ELSE 'OK'
        END AS status
    FROM public.inventory i
    JOIN public.products p
        ON p.id = i.product_id
    ORDER BY
        CASE
            WHEN i.quantity_on_hand <= 0 THEN 1
            WHEN i.quantity_on_hand <= p.reorder_level THEN 2
            ELSE 3
        END,
        i.quantity_on_hand
    """
)


st.subheader("Inventory Status")

st.dataframe(
    inventory,
    use_container_width=True,
    hide_index=True,
)


if st.button("← Back to Home"):
    st.switch_page("app.py")