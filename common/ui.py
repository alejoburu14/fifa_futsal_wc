"""
UI helpers for consistent sidebar and page-link rendering.

This module centralizes small UI conveniences so that every page has a
consistent sidebar header and page navigation. It also provides a helper to
conditionally render page links only when the target file exists.
"""

#Import libraries
from __future__ import annotations
from pathlib import Path
import streamlit as st

# Project root directory (one level above the `common` package)
APP_ROOT = Path(__file__).resolve().parents[1]

def _link_if_exists(rel_path: str, label: str, icon: str = "📄"):
    """Safely add a page link if the target file exists."""
    target = (APP_ROOT / rel_path)
    if target.exists():
        # Streamlit expects an app-relative path with forward slashes
        st.sidebar.page_link(rel_path.replace("\\", "/"), label=label, icon=icon)

def sidebar_header(user: str | None, show_custom_nav: bool = False):
    # Hide Streamlit's auto page list so only our links show
    st.markdown("<style>[data-testid='stSidebarNav']{display:none !important;}</style>", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown(f"**Signed in as:** {user or '—'}")

        if show_custom_nav:
            st.divider()
            st.markdown("#### Pages")
            st.page_link("main.py", label="Home", icon="🏠")
            st.page_link("pages/2_Statistics.py", label="Statistics", icon="📊")
            st.page_link("pages/3_Team_Profiles.py", label="Team Profiles", icon="⚽")
            st.page_link("pages/4_Infographic.py", label="Infographic", icon="🖼️")
