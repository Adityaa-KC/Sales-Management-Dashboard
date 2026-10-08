import streamlit as st
import pandas as pd
from sqlalchemy import text

from app.database.connection import get_engine
from app.utils.ui import page_header


st.set_page_config(
    page_title="Demand Forecast",
    page_icon="📈",
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
    "📈 Demand Forecast",
    "Analyse historical demand and support inventory planning",
)


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


if trend.empty:

    st.warning(
        "There is not enough transaction history "
        "to generate a forecast."
    )

else:

    trend["sale_date"] = pd.to_datetime(
        trend["sale_date"]
    )

    st.subheader("Historical Sales")

    st.line_chart(
        trend.set_index("sale_date")
    )

    st.info(
        """
        Forecasting should be applied when sufficient historical
        time-series data is available. The model can use historical
        demand to estimate future requirements and support reorder
        planning.
        """
    )


if st.button("← Back to Home"):
    st.switch_page("app.py")