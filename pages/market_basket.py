import streamlit as st

from app.utils.ui import page_header, metric_card


st.set_page_config(
    page_title="Market Basket Analysis",
    page_icon="🧺",
    layout="wide",
)


page_header(
    "🧺 Market Basket Analysis",
    "Discover products frequently purchased together",
)


c1, c2, c3 = st.columns(3)

with c1:
    metric_card(
        "Top Association",
        "Pending",
        "Run association analysis",
    )

with c2:
    metric_card(
        "Support",
        "—",
        "Generated from transactions",
    )

with c3:
    metric_card(
        "Confidence",
        "—",
        "Generated from transactions",
    )


st.divider()

st.info(
    """
    Market Basket Analysis is the analytical module for
    identifying products that are frequently purchased together.

    The production implementation can use FP-Growth or
    Apriori to generate association rules.
    """
)


st.subheader("Recommendation")

st.write(
    "Recommendations will appear here after association "
    "rules are generated from transaction data."
)


if st.button("← Back to Home"):
    st.switch_page("app.py")