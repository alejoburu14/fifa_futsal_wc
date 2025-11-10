import streamlit as st
from typing import Dict, List, Optional
from dotenv import load_dotenv

from controllers.auth_controller import login_page
from controllers.data_controller import load_matches, load_match_datasets
from common.utils import sort_matches_for_select, selectbox_with_placeholder
from common.ui import sidebar_header   # <-- NEW
from common.colors import pick_match_colors
from common.metrics import parse_time_to_seconds

st.set_page_config(page_title="Futsal WC — Home", layout="wide")
load_dotenv(override=False)

def main():
    user = login_page()
    assert user

    # Consistent sidebar header ABOVE page links
    sidebar_header(user=user, show_custom_nav=True)

    st.title("🏆 FIFA Futsal World Cup — Matches & Timelines")
    st.caption("Select a match below. The attacking timeline will appear under the box.")

    # 4) Load matches
    with st.spinner("Loading matches..."):
        df_matches = load_matches()
    if df_matches.empty:
        st.warning("No matches retrieved from the API.")
        return

    # 5) Select box (Groups → Stage → Date → MatchName ordering)
    st.subheader("Select a match")
    df_sorted = sort_matches_for_select(df_matches)

    labels = df_sorted.apply(
        lambda r: f'{r["GroupName"]} | {r["StageName"]} | {r["MatchName"]} | {r["KickoffDate"]}',
        axis=1
    ).tolist()
    ids = df_sorted["MatchId"].astype(str).tolist()

    # Make labels unique if needed
    label_to_id: Dict[str, str] = {}
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

    labels = list(label_to_id.keys())         # refresh (unique) labels
    ids = list(label_to_id.values())

    # --- Restore previous selection if we have one ---
    default_index = None
    prev_id = st.session_state.get("selected_match_id")
    if prev_id and prev_id in ids:
        default_index = ids.index(prev_id)

    selected_label = selectbox_with_placeholder(
        "Choose a match to view its timeline:",
        labels,
        key="home_match_select",               # stable widget key across reruns/pages
        default_index=default_index,           # keep selection when returning from Statistics
    )

    if not selected_label:
        st.stop()

    match_id = label_to_id.get(selected_label)
    if not match_id:
        st.stop()

    # Persist for other pages (and for future preselect on Home)
    st.session_state["selected_match_id"] = match_id

    match_row = df_matches.loc[df_matches["MatchId"].astype(str) == str(match_id)]
    if match_row.empty:
        st.error("Match not found.")
        st.stop()
    match_row = match_row.iloc[0]
    st.session_state["match_row"] = match_row.to_dict()

    # 6) Persist selection for the Statistics page
    match_row = df_matches.loc[df_matches["MatchId"].astype(str) == str(match_id)]
    if match_row.empty:
        st.error("Match not found.")
        st.stop()
    match_row = match_row.iloc[0]
    st.session_state["match_row"] = match_row.to_dict()

    pal = pick_match_colors(
        home_name=match_row["HomeName"],
        away_name=match_row["AwayName"],
        home_id=str(match_row["HomeId"]),
        away_id=str(match_row["AwayId"]),
    )
    st.session_state["team_colors"] = {"home": pal.home_color, "away": pal.away_color}

    # 7) Timeline directly under the select box
    with st.spinner(f'Loading timeline for {match_row["MatchName"]}...'):
        events, squads, timeline = load_match_datasets(match_row)

    st.header("Timeline — Attacking Actions")

    # Compute the final score from full events (Goal!)
    goals = events[events["Description"] == "Goal!"].copy()
    goals["TeamId"] = goals["TeamId"].astype(str)
    home_goals = int((goals["TeamId"] == str(match_row["HomeId"])).sum())
    away_goals = int((goals["TeamId"] == str(match_row["AwayId"])).sum())

    st.caption(
        f'**Group:** {match_row["GroupName"]}  |  '
        f'**Stage:** {match_row["StageName"]}  |  '
        f'**Match:** {match_row["MatchName"]}  |  '
        f'**Date:** {match_row.get("KickoffDate", "")}  |  '
        f'**Score:** {match_row["HomeName"]} ({home_goals}) - {match_row["AwayName"]} ({away_goals})'
    )
    if timeline.empty:
        st.info("No attacking actions found for this match.")
    else:
        st.dataframe(
            timeline[["Flag", "TeamName", "Description", "MatchMinute", "PlayerName"]],
            use_container_width=True,
            column_config={
                "Flag": st.column_config.ImageColumn(" ", width="small"),
        },
    )

if __name__ == "__main__":
    main()

