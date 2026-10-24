import streamlit as st
import pandas as pd
from app.utils.ui import page_header, metric_card
from app.utils.store_context import render_store_selector, query_df, currency_symbol

st.set_page_config(page_title="Analytics Dashboard", page_icon="📊", layout="wide")
store = render_store_selector()
if store is None: st.stop()
store_id, store_name, currency = store
symbol = currency_symbol(currency)
page_header("📊 Analytics Dashboard", "Sales performance and business intelligence")
st.caption(f"Active store: {store_name} ({currency})")
stats = query_df("""
 SELECT COALESCE(SUM(total_amount),0) AS revenue, COUNT(*) AS sales, COUNT(DISTINCT customer_id) AS customers
 FROM public.sales WHERE store_id=CAST(:store_id AS UUID) AND status='completed'
""", {"store_id": store_id}).iloc[0]
c1,c2,c3=st.columns(3)
with c1: metric_card("Revenue", f"{symbol}{float(stats['revenue']):,.2f}", f"{currency} · Completed sales")
with c2: metric_card("Sales", f"{int(stats['sales']):,}", "Transactions")
with c3: metric_card("Customers", f"{int(stats['customers']):,}", "Identified customers with purchases")
st.divider()
st.subheader("Revenue by Product")
df=query_df("""
 SELECT p.name AS product, SUM(si.line_total) AS revenue
 FROM public.sale_items si JOIN public.products p ON p.id=si.product_id AND p.store_id=si.store_id
 JOIN public.sales s ON s.id=si.sale_id AND s.store_id=si.store_id
 WHERE si.store_id=CAST(:store_id AS UUID) AND s.status='completed'
 GROUP BY p.id,p.name ORDER BY revenue DESC LIMIT 20
""", {"store_id":store_id})
if not df.empty: st.bar_chart(df.set_index("product"))
else: st.info("No completed sale lines exist for this store yet.")
st.subheader("Sales Trend")
trend=query_df("""
 SELECT DATE(sold_at) AS sale_date, SUM(total_amount) AS revenue
 FROM public.sales WHERE store_id=CAST(:store_id AS UUID) AND status='completed'
 GROUP BY DATE(sold_at) ORDER BY sale_date
""", {"store_id":store_id})
if not trend.empty:
 trend["sale_date"]=pd.to_datetime(trend["sale_date"]); st.line_chart(trend.set_index("sale_date"))
if st.button("← Back to Home"): st.switch_page("app.py")
