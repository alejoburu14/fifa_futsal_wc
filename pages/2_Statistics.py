import streamlit as st
import pandas as pd
from controllers.data_controller import load_match_datasets
from controllers.stats_controller import compute_event_stats

st.set_page_config(page_title="Statistics", layout="wide")

def _ensure_match_selected():
    if "match_row" not in st.session_state or st.session_state["match_row"] is None:
        st.info("Go to **Home** to select a match first.")
        st.stop()

def main():
    _ensure_match_selected()
    match_row = pd.Series(st.session_state["match_row"])
    events, squads, timeline = load_match_datasets(match_row)
    counts, dist = compute_event_stats(events, match_row)

    st.header("Statistics")
    st.caption("Computed from the full timeline (before filtering attacking actions).")

    st.subheader("Count of events by team")
    st.dataframe(counts, use_container_width=True)

    st.subheader("Event distribution by team")
    st.caption("Events: Attempt at Goal, Foul, Goal!, Assist, Corner")
    st.dataframe(dist, use_container_width=True)

if __name__ == "__main__":
    main()
