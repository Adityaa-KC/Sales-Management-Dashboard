import streamlit as st
from app.utils.ui import page_header, metric_card
from app.utils.store_context import render_store_selector, query_df, currency_symbol

st.set_page_config(page_title="Customers & Segments",page_icon="👥",layout="wide")
store=render_store_selector()
if store is None: st.stop()
store_id,store_name,currency=store; symbol=currency_symbol(currency)
page_header("👥 Customers & Segments","Understand customer purchasing behaviour")
st.caption(f"Active store: {store_name} ({currency})")
stats=query_df("SELECT COUNT(*) AS customers FROM public.customers WHERE store_id=CAST(:store_id AS UUID)",{"store_id":store_id}).iloc[0]
revenue=query_df("SELECT COALESCE(SUM(total_amount),0) AS revenue FROM public.sales WHERE store_id=CAST(:store_id AS UUID) AND status='completed'",{"store_id":store_id}).iloc[0]["revenue"]
a,b=st.columns(2)
with a: metric_card("Customers",f"{int(stats['customers']):,}","Registered / identified customers")
with b: metric_card("Customer Revenue",f"{symbol}{float(revenue):,.2f}",f"Completed sales ({currency})")
customers=query_df("""
 SELECT c.name AS customer,COUNT(s.id) AS purchases,COALESCE(SUM(s.total_amount),0) AS spending
 FROM public.customers c LEFT JOIN public.sales s ON s.customer_id=c.id AND s.store_id=c.store_id AND s.status='completed'
 WHERE c.store_id=CAST(:store_id AS UUID) GROUP BY c.id,c.name ORDER BY spending DESC
""",{"store_id":store_id})
st.subheader("Customer Purchasing Behaviour")
st.dataframe(customers,use_container_width=True,hide_index=True)
st.info("RFM segmentation will use the selected store's database transactions. UCI customer labels are synthetic IDs, not names or contact details from the source.")
if st.button("← Back to Home"): st.switch_page("app.py")
