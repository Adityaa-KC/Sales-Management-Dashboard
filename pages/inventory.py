import streamlit as st
from app.utils.ui import page_header, metric_card
from app.utils.store_context import render_store_selector, query_df

st.set_page_config(page_title="Inventory Management", page_icon="📦", layout="wide")
store=render_store_selector()
if store is None: st.stop()
store_id,store_name,currency=store
page_header("📦 Inventory Management","Monitor stock levels and reorder requirements")
st.caption(f"Active store: {store_name} ({currency})")
stats=query_df("""
 SELECT COALESCE(SUM(i.quantity_on_hand),0) AS total_stock,COUNT(*) AS tracked_products,
 COUNT(*) FILTER(WHERE i.quantity_on_hand<=0) AS out_of_stock,
 COUNT(*) FILTER(WHERE i.quantity_on_hand<=p.reorder_level) AS low_stock
 FROM public.inventory i JOIN public.products p ON p.id=i.product_id AND p.store_id=i.store_id
 WHERE i.store_id=CAST(:store_id AS UUID)
""", {"store_id":store_id}).iloc[0]
a,b,c,d=st.columns(4)
with a: metric_card("📦 Inventory",f"{int(stats['total_stock']):,}","Known units on hand")
with b: metric_card("Tracked Products",f"{int(stats['tracked_products']):,}","Products with inventory records")
with c: metric_card("⚠ Low Stock",f"{int(stats['low_stock']):,}","Needs attention")
with d: metric_card("🚫 Out of Stock",f"{int(stats['out_of_stock']):,}","Tracked as zero or less")
inventory=query_df("""
 SELECT p.sku,p.name AS product,i.quantity_on_hand AS stock,p.reorder_level,
 CASE WHEN i.quantity_on_hand<=0 THEN 'OUT OF STOCK' WHEN i.quantity_on_hand<=p.reorder_level THEN 'LOW STOCK' ELSE 'OK' END AS status
 FROM public.inventory i JOIN public.products p ON p.id=i.product_id AND p.store_id=i.store_id
 WHERE i.store_id=CAST(:store_id AS UUID)
 ORDER BY CASE WHEN i.quantity_on_hand<=0 THEN 1 WHEN i.quantity_on_hand<=p.reorder_level THEN 2 ELSE 3 END,i.quantity_on_hand
""", {"store_id":store_id})
st.subheader("Inventory Status")
if inventory.empty:
 st.warning("No inventory snapshot exists for this store. Historical UCI sales do not include current stock quantities, so stock levels and reorder alerts cannot be inferred.")
else: st.dataframe(inventory,use_container_width=True,hide_index=True)
if st.button("← Back to Home"): st.switch_page("app.py")
