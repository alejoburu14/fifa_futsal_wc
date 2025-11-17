"""
Authentication helpers for the Streamlit app.

This module provides a lightweight cookie-based login flow used by the
application. It intentionally avoids heavyweight third-party auth so the
project stays simple for academic purposes.

Key functions:
    - `login_page()`: render a login form or perform auto-login from cookie.
    - `logout_button()`: place a logout button in the sidebar that clears
        session state and expires the cookie.

Implementation notes:
    - The module uses `extra_streamlit_components.CookieManager` to persist a
        small cookie that keeps the user logged between runs if requested.
    - Session state keys like `authenticated` and `username` are used across
        the app to gate page access; clearing them is how logout works.
"""

# Import libraries
from __future__ import annotations
import os
from datetime import timedelta
import streamlit as st
import extra_streamlit_components as stx

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

    # Instantiate a CookieManager component that we will use both to read
    # and to set the authentication cookie. The key ensures the component
    # instance is unique within a Streamlit run.
    cm = stx.CookieManager(key=CM_KEY_MAIN)

    # If the user just logged out we set a temporary `force_logout` flag in
    # session_state to prevent immediate auto-login from the cookie. Pop the
    # flag so it applies only to the current run.
    force_logout = bool(st.session_state.pop("force_logout", False))
    if not force_logout:
        # Try to read existing cookies. This may fail in some envs so guard
        # with try/except and treat failures as 'no cookie'.
        try:
            cookies = cm.get_all() or {}
        except Exception:
            cookies = {}

        # If a known username is present in the cookie and matches our
        # configured users list, set session_state and treat the user as
        # authenticated (auto-login path).
        user_from_cookie = cookies.get(COOKIE_NAME)
        if user_from_cookie and user_from_cookie in users:
            st.session_state["authenticated"] = True
            st.session_state["username"] = user_from_cookie
            return user_from_cookie, None
    else:
        # As a belt-and-suspenders approach, try to delete the cookie on
        # the main CookieManager if we are forcing a logout.
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
            # Persist the login in a cookie when the user requested "remember".
            # - If `remember` is True we set a persistent cookie with a
            #   max_age; otherwise we set a session cookie that expires when
            #   the browser is closed.
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
                # Ignore cookie-setting errors; authentication remains in
                # session_state which is sufficient for the current run.
                pass

            # Rerun the script so pages that depend on authenticated state
            # render immediately.
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

    # Render a logout button in the sidebar. When clicked we do three things:
    #  1) set a `force_logout` flag in session_state so the immediate next
    #     run won't auto-login from the cookie,
    #  2) attempt to delete/expire the cookie by several methods for
    #     compatibility with different versions of the cookie component, and
    #  3) clear the relevant session_state keys and rerun.
    with st.sidebar:
        if st.button("Logout", key="logout_btn"):
            # mark the next run to SKIP cookie auto-login
            st.session_state["force_logout"] = True

            # Try multiple methods to ensure the cookie is deleted on the
            # user's browser; some versions of the cookie manager support
            # `delete`, others rely on setting an expired value.
            for op in (
                lambda: cm_side.delete(COOKIE_NAME),
                lambda: cm_side.set(COOKIE_NAME, "", max_age=0),
                lambda: cm_side.set(COOKIE_NAME, "", expires_days=-1),
            ):
                try:
                    op()
                except Exception:
                    # Ignore failures to maximize robustness across envs.
                    pass

            # Clear relevant session state keys used across the app.
            for k in (
                "authenticated", "username", "remember",
                "selected_match_id", "match_row", "team_colors",
            ):
                st.session_state.pop(k, None)

            # Trigger a rerun so the UI immediately reflects the logged-out state.
            _safe_rerun()
