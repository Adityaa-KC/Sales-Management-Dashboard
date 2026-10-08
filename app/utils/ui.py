import streamlit as st


def page_header(title: str, subtitle: str):
    st.markdown(
        f"""
        <div style="
            padding: 10px 0 25px 0;
        ">
            <h1 style="
                margin-bottom: 5px;
                font-size: 42px;
            ">
                {title}
            </h1>
            <p style="
                color: #6b7280;
                font-size: 18px;
                margin-top: 0;
            ">
                {subtitle}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(title, value, subtitle=""):
    st.html(
        f"""
<div style="
    background: white;
    padding: 24px;
    border-radius: 18px;
    min-height: 130px;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.06);
    margin-bottom: 10px;
">

    <div style="
        color: #6b7280;
        font-size: 16px;
        margin-bottom: 10px;
    ">
        {title}
    </div>

    <div style="
        font-size: 32px;
        font-weight: 700;
        color: #172033;
    ">
        {value}
    </div>

    <div style="
        color: #4b8f4b;
        margin-top: 8px;
        font-size: 14px;
    ">
        {subtitle}
    </div>

</div>
"""
    )


def module_button(label, icon, page):
    if st.button(
        f"{icon}  {label}",
        use_container_width=True,
    ):
        st.switch_page(page)