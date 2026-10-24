import streamlit as st
import pandas as pd
from app.utils.ui import page_header
from app.utils.store_context import render_store_selector, query_df, currency_symbol

st.set_page_config(page_title="Demand Forecast",page_icon="📈",layout="wide")
store=render_store_selector()
if store is None: st.stop()
store_id,store_name,currency=store; symbol=currency_symbol(currency)
page_header("📈 Demand Forecast","Analyse historical demand and support inventory planning")
st.caption(f"Active store: {store_name} ({currency})")
trend=query_df("""
 SELECT DATE(sold_at) AS sale_date,SUM(total_amount) AS revenue
 FROM public.sales WHERE store_id=CAST(:store_id AS UUID) AND status='completed'
 GROUP BY DATE(sold_at) ORDER BY sale_date
""",{"store_id":store_id})
if trend.empty: st.warning("No completed transaction history is available for this store.")
else:
 trend["sale_date"]=pd.to_datetime(trend["sale_date"])
 st.subheader("Historical Revenue")
 st.line_chart(trend.set_index("sale_date"))
 if len(trend)<30: st.warning(f"Only {len(trend)} distinct sales days are available. This is not enough for a dependable forecast; use the chart as historical context only.")
 else: st.info("Historical data is loaded from PostgreSQL. Forecast model integration and holdout evaluation are the next analytics step.")
if st.button("← Back to Home"): st.switch_page("app.py")
