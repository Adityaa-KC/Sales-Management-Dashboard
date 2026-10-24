import streamlit as st
from app.utils.ui import page_header, metric_card
from app.utils.store_context import render_store_selector, query_df, currency_symbol

st.set_page_config(page_title="Sales Management", page_icon="🛒", layout="wide")
store=render_store_selector()
if store is None: st.stop()
store_id, store_name, currency=store; symbol=currency_symbol(currency)
page_header("🛒 Sales Management", "Monitor sales performance and recent transactions")
st.caption(f"Active store: {store_name} ({currency})")
stats=query_df("""
 SELECT COALESCE(SUM(total_amount),0) AS revenue, COUNT(*) AS transactions, COALESCE(AVG(total_amount),0) AS average_bill
 FROM public.sales WHERE store_id=CAST(:store_id AS UUID) AND status='completed'
""", {"store_id":store_id}).iloc[0]
c1,c2,c3=st.columns(3)
with c1: metric_card("Revenue",f"{symbol}{float(stats['revenue']):,.2f}",f"{currency} · Completed sales")
with c2: metric_card("Transactions",f"{int(stats['transactions']):,}","Completed transactions")
with c3: metric_card("Average Bill",f"{symbol}{float(stats['average_bill']):,.2f}",f"Average transaction ({currency})")
st.divider(); st.subheader("🏆 Top Selling Products")
products=query_df("""
 SELECT p.name AS product,SUM(si.quantity) AS units_sold,SUM(si.line_total) AS revenue
 FROM public.sale_items si JOIN public.products p ON p.id=si.product_id AND p.store_id=si.store_id
 JOIN public.sales s ON s.id=si.sale_id AND s.store_id=si.store_id
 WHERE si.store_id=CAST(:store_id AS UUID) AND s.status='completed'
 GROUP BY p.id,p.name ORDER BY revenue DESC LIMIT 10
""", {"store_id":store_id})
if products.empty: st.info("No completed sale lines are available for this store.")
else:
 a,b=st.columns([1,2])
 with a: st.success(f"🏆 {products.iloc[0]['product']}")
 with b: st.bar_chart(products.set_index("product")["revenue"])
st.divider(); st.subheader("Recent Transactions")
transactions=query_df("""
 SELECT s.sale_number AS transaction,COALESCE(c.name,'Walk-in Customer') AS customer,s.sold_at AS date,s.total_amount AS amount
 FROM public.sales s LEFT JOIN public.customers c ON c.id=s.customer_id AND c.store_id=s.store_id
 WHERE s.store_id=CAST(:store_id AS UUID) AND s.status='completed'
 ORDER BY s.sold_at DESC LIMIT 20
""", {"store_id":store_id})
st.dataframe(transactions,use_container_width=True,hide_index=True)
if st.button("← Back to Home"): st.switch_page("app.py")
