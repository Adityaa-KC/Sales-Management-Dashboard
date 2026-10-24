import streamlit as st
from app.utils.ui import page_header, metric_card, module_button
from app.utils.store_context import render_store_selector, query_df, currency_symbol

st.set_page_config(page_title="Smart Retail", page_icon="🛒", layout="wide")
store = render_store_selector()
if store is None:
    st.stop()
store_id, store_name, currency = store
symbol = currency_symbol(currency)
page_header("Smart Retail", "Sales Management & Inventory Intelligence")
st.caption(f"Active store: **{store_name}** · Currency: **{currency}** · All metrics are filtered to this store.")

overview = query_df("""
    SELECT
      COALESCE((SELECT SUM(i.quantity_on_hand) FROM public.inventory i WHERE i.store_id = CAST(:store_id AS UUID)), 0) AS inventory_units,
      COALESCE((SELECT SUM(s.total_amount) FROM public.sales s WHERE s.store_id = CAST(:store_id AS UUID) AND s.status='completed'), 0) AS revenue,
      COALESCE((SELECT COUNT(*) FROM public.sales s WHERE s.store_id = CAST(:store_id AS UUID) AND s.status='completed'), 0) AS transactions,
      COALESCE((SELECT COUNT(*) FROM public.products p WHERE p.store_id = CAST(:store_id AS UUID) AND p.is_active=TRUE), 0) AS products
""", {"store_id": store_id}).iloc[0]
low_stock = query_df("""
    SELECT COUNT(*) AS count FROM public.inventory i
    JOIN public.products p ON p.id=i.product_id AND p.store_id=i.store_id
    WHERE i.store_id=CAST(:store_id AS UUID) AND i.quantity_on_hand <= p.reorder_level
""", {"store_id": store_id}).iloc[0]["count"]

st.subheader("Business Overview")
c1, c2, c3 = st.columns(3)
with c1:
    if store_name == "UCI Online Retail Demo":
        metric_card("📦 Inventory Level", "Unknown", "UCI has no current stock snapshot")
    else:
        metric_card("📦 Inventory Level", f"{int(overview['inventory_units']):,}", f"⚠ {int(low_stock)} items below reorder")
with c2: metric_card("🛒 Total Sales", f"{int(overview['transactions']):,}", "Completed transactions")
with c3: metric_card("💰 Revenue", f"{symbol}{float(overview['revenue']):,.2f}", f"{currency} · Selected store total")
st.divider()
st.subheader("Quick Access")
row1 = st.columns(3)
with row1[0]: module_button("Sales Management", "🛒", "pages/sales.py")
with row1[1]: module_button("Inventory Management", "📦", "pages/inventory.py")
with row1[2]: module_button("Analytics Dashboard", "📊", "pages/analytics.py")
row2 = st.columns(3)
with row2[0]: module_button("Market Basket Analysis", "🧺", "pages/market_basket.py")
with row2[1]: module_button("Customers & Segments", "👥", "pages/Customers_and_Segments.py")
with row2[2]: module_button("Demand Forecast", "📈", "pages/Demand_Forecast.py")
st.divider()
st.subheader("⚠️ Inventory Alerts")
alerts = query_df("""
    SELECT p.name AS product, i.quantity_on_hand AS stock, p.reorder_level
    FROM public.inventory i JOIN public.products p ON p.id=i.product_id AND p.store_id=i.store_id
    WHERE i.store_id=CAST(:store_id AS UUID) AND i.quantity_on_hand <= p.reorder_level
    ORDER BY i.quantity_on_hand ASC
""", {"store_id": store_id})
if store_name == "UCI Online Retail Demo":
    st.info("This is historical transaction data. UCI does not provide current stock counts, so inventory alerts are unavailable for this demo store.")
elif alerts.empty:
    st.success("All tracked products are above their reorder levels.")
else:
    st.warning(f"{len(alerts)} product(s) require attention.")
    st.dataframe(alerts, use_container_width=True, hide_index=True)
