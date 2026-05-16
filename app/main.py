"""Streamlit entry point — sidebar navigation."""

import streamlit as st

st.set_page_config(
    page_title="BRN Portfolio",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("BRN Portfolio")
st.markdown(
    """
    A personal **CAC 40** portfolio management tool.

    Use the sidebar to navigate between pages:

    | Page | Description |
    |------|-------------|
    | **1 — Market** | CAC 40 overview and per-stock drill-down |
    | **2 — Portfolio** | Input your allocation and view current performance |
    | **3 — Optimizer** | Markowitz efficient frontier and optimal weights |
    | **4 — Advice** | Rebalancing recommendations |
    """
)
