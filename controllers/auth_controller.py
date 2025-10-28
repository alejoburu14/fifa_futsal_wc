from typing import Optional
import streamlit as st
from common.utils import get_users, safe_rerun

def login_page() -> Optional[str]:
    if st.session_state.get("authenticated") and st.session_state.get("username"):
        return st.session_state["username"]

    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    .block-container { padding-top: 6vh; max-width: 640px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("# 🔐 Sign in")
    st.caption("Use your credentials. Defaults are **admin/admin** if no secrets are set.")

    with st.form("login_form"):
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        ok = st.form_submit_button("Sign in")

    if ok:
        users = get_users()
        if user in users and pwd == users[user]:
            st.session_state["authenticated"] = True
            st.session_state["username"] = user
            safe_rerun()
        else:
            st.error("Invalid username or password.")
    st.stop()
