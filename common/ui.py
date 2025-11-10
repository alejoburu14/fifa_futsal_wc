import streamlit as st

def sidebar_header(user: str | None = None, show_custom_nav: bool = True):
    """Render a consistent sidebar header across all pages: Signed in / Logout and page links."""
    has_page_link = hasattr(st.sidebar, "page_link")
    with st.sidebar:
        # Hide Streamlit's default Pages nav so our custom links sit at the top
        if show_custom_nav and has_page_link:
            st.markdown(
                """
                <style>
                [data-testid="stSidebarNav"] { display: none !important; }
                </style>
                """,
                unsafe_allow_html=True,
            )

        # Signed in / Logout
        if user:
            st.caption(f"Signed in as **{user}**")
        else:
            st.caption("Signed in")

        if st.button("Logout", use_container_width=True, key="logout-btn"):
            st.session_state.clear()
            if hasattr(st, "rerun"): st.rerun()
            else: st.experimental_rerun()

        st.divider()

        # Custom page links (only if supported by your Streamlit version)
        if show_custom_nav and has_page_link:
            st.subheader("Pages")
            st.sidebar.page_link("main.py", label="Home", icon="🏠")
            st.sidebar.page_link("pages/2_Statistics.py", label="Statistics", icon="📊")