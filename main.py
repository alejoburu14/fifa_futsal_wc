import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from controllers.auth_controller import login_page
from controllers.data_controller import load_matches
from common.utils import sort_matches_for_select, selectbox_with_placeholder

st.set_page_config(page_title="Futsal WC — Home", layout="wide")
load_dotenv(override=False)

def main():
    user = login_page()
    assert user

    st.sidebar.success(f"Signed in as **{user}**")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        if hasattr(st, "rerun"): st.rerun()
        else: st.experimental_rerun()

    st.title("🏆 FIFA Futsal World Cup — Matches & Timelines")
    st.caption("Select a match (Groups first, then knockouts). Then open **Timeline** or **Statistics** from the sidebar.")

    with st.spinner("Loading matches..."):
        df_matches = load_matches()
    if df_matches.empty:
        st.warning("No matches retrieved from the API.")
        return

    st.subheader("Select a match")
    df_sorted = sort_matches_for_select(df_matches)
    labels = df_sorted.apply(lambda r: f'{r["GroupName"]} | {r["StageName"]} | {r["MatchName"]} | {r["KickoffDate"]}', axis=1).tolist()
    ids = df_sorted["MatchId"].astype(str).tolist()

    label_to_id = {}
    for lab, mid in zip(labels, ids):
        if lab not in label_to_id:
            label_to_id[lab] = mid
        else:
            c = 2
            new_lab = f"{lab} ({c})"
            while new_lab in label_to_id:
                c += 1
                new_lab = f"{lab} ({c})"
            label_to_id[new_lab] = mid

    selected = selectbox_with_placeholder("Choose a match to view its timeline:", list(label_to_id.keys()), key="home_match_select")
    if not selected:
        st.stop()

    match_id = label_to_id.get(selected)
    if not match_id:
        st.stop()

    match_row = df_matches.loc[df_matches["MatchId"].astype(str) == str(match_id)]
    if match_row.empty:
        st.error("Match not found.")
        st.stop()
    st.session_state["match_row"] = match_row.iloc[0].to_dict()
    st.success("Match selected. Open **Timeline** or **Statistics** from the sidebar.")

if __name__ == "__main__":
    main()
