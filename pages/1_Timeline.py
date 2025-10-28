import streamlit as st
import pandas as pd
from controllers.data_controller import load_match_datasets

st.set_page_config(page_title="Timeline", layout="wide")

def _ensure_match_selected():
    if "match_row" not in st.session_state or st.session_state["match_row"] is None:
        st.info("Go to **Home** to select a match first.")
        st.stop()

def main():
    _ensure_match_selected()
    match_row = pd.Series(st.session_state["match_row"])
    events, squads, timeline = load_match_datasets(match_row)

    st.header("Timeline — Attacking Actions")
    st.caption(
        f'**Group:** {match_row["GroupName"]}  |  '
        f'**Stage:** {match_row["StageName"]}  |  '
        f'**Match:** {match_row["MatchName"]}  |  '
        f'**Date:** {match_row.get("KickoffDate", "")}'
    )
    if timeline.empty:
        st.info("No attacking actions found for this match.")
    else:
        st.dataframe(timeline, use_container_width=True)

if __name__ == "__main__":
    main()
