# common/ui.py
from __future__ import annotations
from pathlib import Path
import streamlit as st

# Project root = .../fifa_futsal_wc
APP_ROOT = Path(__file__).resolve().parents[1]

def _link_if_exists(rel_path: str, label: str, icon: str = "📄"):
    """Safely add a page link if the target file exists."""
    target = (APP_ROOT / rel_path)
    if target.exists():
        # Streamlit expects an app-relative path with forward slashes
        st.sidebar.page_link(rel_path.replace("\\", "/"), label=label, icon=icon)

def sidebar_header(user: str | None, show_custom_nav: bool = False):
    # Hide the built-in pages nav so only our custom links appear
    st.markdown(
        "<style>[data-testid='stSidebarNav']{display:none !important;}</style>",
        unsafe_allow_html=True,
    )
    with st.sidebar:
        st.markdown("**Signed in as:** " + (user or "—"))
        if st.button("Logout"):
            st.session_state.clear()
            if hasattr(st, "rerun"): st.rerun()
            else: st.experimental_rerun()

        if show_custom_nav:
            st.divider()
            st.markdown("#### Pages")
            st.page_link("main.py", label="Home", icon="🏠")
            st.page_link("pages/2_Statistics.py", label="Statistics", icon="📊")
            st.page_link("pages/3_Infographic.py", label="Infographic", icon="🖼️")
