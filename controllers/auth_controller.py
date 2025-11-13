# controllers/auth_controller.py
from __future__ import annotations
import os
from datetime import timedelta
import streamlit as st
import extra_streamlit_components as stx  # pip install extra-streamlit-components

# ----- Config (env or defaults) -----
COOKIE_NAME  = os.getenv("FFWC_COOKIE_NAME", "ffwc_user")
COOKIE_DAYS  = int(os.getenv("FFWC_COOKIE_DAYS", "7"))
APP_USER     = os.getenv("APP_USER", "admin")
APP_PASSWORD = os.getenv("APP_PASSWORD", "admin")

# Unique keys for cookie components (must not collide in one run)
CM_KEY_MAIN    = "ffwc_cookie_component_main"
CM_KEY_SIDEBAR = "ffwc_cookie_component_sidebar"

def _safe_rerun() -> None:
    if hasattr(st, "rerun"): st.rerun()
    elif hasattr(st, "experimental_rerun"): st.experimental_rerun()
    else: st.stop()

def _get_users() -> dict[str, str]:
    try:
        if "auth" in st.secrets and "users" in st.secrets["auth"]:
            return dict(st.secrets["auth"]["users"])
    except Exception:
        pass
    return {APP_USER: APP_PASSWORD}

def login_page():
    """
    Returns (username, None) when authenticated.
    Handles cookie auto-login unless a force-logout flag is present.
    """
    users = _get_users()

    # Already authenticated this run?
    if st.session_state.get("authenticated") and st.session_state.get("username"):
        return st.session_state["username"], None

    # Mount MAIN CookieManager once per run
    cm = stx.CookieManager(key=CM_KEY_MAIN)

    # If we just clicked logout, skip auto-login and ensure deletion again
    force_logout = bool(st.session_state.pop("force_logout", False))
    if not force_logout:
        try:
            cookies = cm.get_all() or {}
        except Exception:
            cookies = {}
        user_from_cookie = cookies.get(COOKIE_NAME)
        if user_from_cookie and user_from_cookie in users:
            st.session_state["authenticated"] = True
            st.session_state["username"] = user_from_cookie
            return user_from_cookie, None
    else:
        # belt-and-suspenders: delete cookie again on the "main" side
        try:
            cm.delete(COOKIE_NAME)
        except Exception:
            pass

    # Render login UI (hide sidebar only here)
    st.markdown("""
        <style>
          [data-testid="stSidebar"] { display: none; }
          .block-container { padding-top: 10vh; max-width: 560px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("## Login")
    with st.form("login_form", clear_on_submit=False):
        user = st.text_input("Username")
        pwd  = st.text_input("Password", type="password")
        remember = st.checkbox("Remember for this session", value=True)
        ok = st.form_submit_button("Login")

    if ok:
        if user in users and pwd == users[user]:
            st.session_state["authenticated"] = True
            st.session_state["username"] = user
            st.session_state["remember"] = remember

            # Always set a cookie so refresh keeps you logged in:
            # - session cookie (no max_age) when remember == False
            # - persistent cookie when remember == True
            try:
                if remember:
                    cm.set(
                        COOKIE_NAME,
                        user,
                        max_age=int(timedelta(days=COOKIE_DAYS).total_seconds()),
                    )
                else:
                    # session cookie: survives refresh, disappears when browser closes
                    cm.set(COOKIE_NAME, user)
            except Exception:
                pass

            _safe_rerun()
        else:
            st.error("Invalid username or password.")
    st.stop()  # block the rest of the app if not authenticated

def logout_button():
    """
    Sidebar logout button using the SIDEBAR cookie component.
    Sets a force-logout flag so the next run won't auto-login from cookie.
    """
    cm_side = stx.CookieManager(key=CM_KEY_SIDEBAR)

    with st.sidebar:
        if st.button("Logout", key="logout_btn"):
            # mark the next run to SKIP cookie auto-login
            st.session_state["force_logout"] = True

            # delete / expire cookie (several methods for robustness)
            for op in (
                lambda: cm_side.delete(COOKIE_NAME),
                lambda: cm_side.set(COOKIE_NAME, "", max_age=0),
                lambda: cm_side.set(COOKIE_NAME, "", expires_days=-1),
            ):
                try:
                    op()
                except Exception:
                    pass

            # Clear app session state
            for k in (
                "authenticated", "username", "remember",
                "selected_match_id", "match_row", "team_colors",
            ):
                st.session_state.pop(k, None)

            _safe_rerun()
