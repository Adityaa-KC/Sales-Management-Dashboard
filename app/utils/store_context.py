"""Shared store selection and safe query helpers for Streamlit pages."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import text

from app.database.connection import get_engine


@st.cache_resource
def get_engine_cached():
    return get_engine()


def get_stores() -> pd.DataFrame:
    engine = get_engine_cached()
    with engine.connect() as conn:
        return pd.read_sql(
            text("SELECT id::text AS id, name, currency FROM public.stores ORDER BY name"),
            conn,
        )


def render_store_selector() -> tuple[str, str, str] | None:
    """Render a consistent store selector; returns (id, name, currency)."""
    try:
        stores = get_stores()
    except Exception as exc:
        st.error(f"Could not load stores from PostgreSQL: {exc}")
        st.stop()
    if stores.empty:
        st.warning("No stores exist in the database. Create a store before using the dashboard.")
        st.stop()
    by_id = {str(row.id): (str(row.name), str(row.currency)) for row in stores.itertuples()}
    current = st.session_state.get("active_store_id")
    if current not in by_id:
        current = str(stores.iloc[0]["id"])
    selected_id = st.sidebar.selectbox(
        "Active store",
        options=list(by_id),
        index=list(by_id).index(current),
        format_func=lambda store_id: f"{by_id[store_id][0]} ({by_id[store_id][1]})",
        key="active_store_id",
        help="Every page uses this store. UCI demonstration data is kept separate from your live store.",
    )
    name, currency = by_id[selected_id]
    st.sidebar.caption(f"Database source: PostgreSQL · {currency}")
    return selected_id, name, currency


def query_df(sql: str, params: dict | None = None) -> pd.DataFrame:
    engine = get_engine_cached()
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def currency_symbol(currency: str) -> str:
    return {"INR": "₹", "GBP": "£", "USD": "$", "EUR": "€"}.get(currency.upper(), f"{currency} ")
