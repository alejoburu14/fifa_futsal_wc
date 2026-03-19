from __future__ import annotations

import pandas as pd
import streamlit as st

from common.ml_labels import CLUSTER_DESCRIPTIONS
from common.team_profiles import compute_team_profile_outputs, plot_team_profiles_pca_plotly
from common.ui import sidebar_header
from controllers.auth_controller import logout_button

st.set_page_config(page_title="Team Profiles", layout="wide")


def _ensure_auth():
    if not st.session_state.get("authenticated"):
        try:
            st.switch_page("main.py")
        except Exception:
            st.info("Please sign in on **Home** first.")
            st.stop()


def _ensure_match_selected():
    if "match_row" not in st.session_state or not st.session_state["match_row"]:
        st.info("Go to **Home** to select a match first.")
        st.stop()


def _get_flags(match_row):
    try:
        from common.flags import get_flags_for_match
        return get_flags_for_match(match_row)
    except Exception:
        try:
            from common.flags import get_flag_url_by_team_id
            return (
                get_flag_url_by_team_id(str(match_row["HomeId"])),
                get_flag_url_by_team_id(str(match_row["AwayId"])),
            )
        except Exception:
            return "", ""


def _metric_definitions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Indicator": [
                "Attempts / Match",
                "Goals / Match",
                "Conversion Rate",
                "Mean Attack Minute",
                "Early Attack Share",
                "Late Attack Share",
                "Attack Variability",
            ],
            "Meaning": [
                "Average number of attacking actions per match.",
                "Average number of goals scored per match.",
                "Share of attacking actions that become goals.",
                "Average minute in which the team produces its attacking actions.",
                "Share of attacks produced in the first half (minute ≤ 20).",
                "Share of attacks produced in the second half (minute > 20).",
                "How spread or concentrated the attacking actions are across match time.",
            ],
        }
    )


def main():
    _ensure_auth()
    sidebar_header(user=st.session_state.get("username"), show_custom_nav=True)
    logout_button()

    _ensure_match_selected()

    match_row = pd.Series(st.session_state["match_row"])
    home_team = str(match_row["HomeName"])
    away_team = str(match_row["AwayName"])
    home_flag, away_flag = _get_flags(match_row)

    with st.spinner("Computing team tactical profiles..."):
        df_profiles, df_cluster_summary, df_attack = compute_team_profile_outputs()

    if df_profiles.empty:
        st.warning("Team profile data could not be computed.")
        st.stop()

    st.title("Team Profiles")
    st.caption(
        "This page compares the tactical profiles of the selected teams and situates them "
        "within the tournament-wide clustering model."
    )

    # Compute the final score from full events (Goal!)
    match_id = str(match_row.get("MatchId", ""))
    events = (
        df_attack[df_attack["MatchId"] == match_id].copy()
        if not df_attack.empty and match_id
        else pd.DataFrame()
    )
    goals = events[events["Description"] == "Goal!"].copy()
    goals["TeamId"] = goals["TeamId"].astype(str)
    home_goals = int((goals["TeamId"] == str(match_row["HomeId"])).sum())
    away_goals = int((goals["TeamId"] == str(match_row["AwayId"])).sum())

    parts = [
        f'**Stage:** {match_row["StageName"]}',
    ]

    # Only add Group if it exists and is meaningful
    group = str(match_row.get("GroupName", "")).strip()
    if group and match_row["StageName"] == "Group Matches":
        parts.append(f'**Group:** {group}')

    parts.extend([
        f'**Match:** {match_row["MatchName"]}',
        f'**Date:** {match_row.get("KickoffDate", "")}',
        f'**Score:** {match_row["HomeName"]} ({home_goals}) - {match_row["AwayName"]} ({away_goals})'
    ])

    st.markdown(" | ".join(parts))

    # ------------------------------------------------------------------
    # Tactical profile framework
    # ------------------------------------------------------------------
    st.markdown("## Tactical profile framework")
    st.caption(
        "Teams are grouped according to attacking behavior across the tournament using a clustering model "
        "based on attacking volume, scoring efficiency, and timing of attacking actions."
    )

    st.subheader("Cluster definitions")
    for label, desc in CLUSTER_DESCRIPTIONS.items():
        st.markdown(f"**{label}** — {desc}")

    # ------------------------------------------------------------------
    # Selected match comparison
    # ------------------------------------------------------------------
    st.markdown("## Selected match comparison")
    st.caption(
        "The table below compares the two selected teams across the indicators used to build tactical profiles."
    )

    st.markdown(
        f"### <img src='{home_flag}' width='35' height='35' style='vertical-align:middle;'> "
        f"{home_team} vs {away_team} "
        f"<img src='{away_flag}' width='35' height='35' style='vertical-align:middle;'>",
        unsafe_allow_html=True,
    )

    compare_cols = [
        "TeamName",
        "ClusterLabel",
        "Attempts_per_Match",
        "Goals_per_Match",
        "Conversion_Rate",
        "Mean_Attack_Minute",
        "Early_Attack_Share",
        "Late_Attack_Share",
        "Attack_Variability",
    ]

    df_two = df_profiles[df_profiles["TeamName"].isin([home_team, away_team])][compare_cols].copy()

    metrics_order = [
        ("ClusterLabel", "Cluster"),
        ("Attempts_per_Match", "Attempts / Match"),
        ("Goals_per_Match", "Goals / Match"),
        ("Conversion_Rate", "Conversion Rate"),
        ("Mean_Attack_Minute", "Mean Attack Minute"),
        ("Early_Attack_Share", "Early Attack Share"),
        ("Late_Attack_Share", "Late Attack Share"),
        ("Attack_Variability", "Attack Variability"),
    ]

    comparison_rows = []
    for metric_col, metric_label in metrics_order:
        row_data = {"Indicator": metric_label}
        for team in [home_team, away_team]:
            val = df_two.loc[df_two["TeamName"] == team, metric_col]
            if val.empty:
                row_data[team] = "N/A"
            else:
                val = val.iloc[0]
                if metric_col in ["Conversion_Rate", "Early_Attack_Share", "Late_Attack_Share"]:
                    row_data[team] = f"{val:.1%}"
                elif metric_col == "ClusterLabel":
                    row_data[team] = str(val)
                else:
                    row_data[team] = f"{val:.2f}"
        comparison_rows.append(row_data)

    df_compare = pd.DataFrame(comparison_rows)

    st.caption("Cluster assignment is shown first, followed by the numerical indicators used in the model.")
    st.dataframe(df_compare, use_container_width=True, hide_index=True)

    defs = _metric_definitions()
    with st.expander("Indicator definitions"):
        st.dataframe(defs, use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------
    # Tournament-wide team clustering
    # ------------------------------------------------------------------
    st.divider()
    st.markdown("## Tournament-wide team clustering")
    st.caption(
        "The following views place the selected teams within the broader tournament clustering structure."
    )

    st.subheader("Tournament team profiles")
    st.caption(
        "All teams are shown alphabetically with their assigned tactical profile. "
        "The two teams selected on Home are highlighted."
    )

    table_cols = [
        "TeamName",
        "ClusterLabel",
        "Attempts_per_Match",
        "Goals_per_Match",
        "Conversion_Rate",
        "Mean_Attack_Minute",
    ]

    df_table = df_profiles[table_cols].copy().sort_values("TeamName").reset_index(drop=True)

    def highlight_selected_teams(row):
        if row["TeamName"] in [home_team, away_team]:
            return ["background-color: #FFF3CD; font-weight: bold;"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df_table.style.apply(highlight_selected_teams, axis=1),
        use_container_width=True,
    )

    # ------------------------------------------------------------------
    # PCA chart
    # ------------------------------------------------------------------
    st.subheader("Cluster visualization (PCA)")
    st.caption(
        "PCA is used only for visualization. It reduces the feature space to two dimensions, "
        "so teams positioned closer together have more similar attacking profiles. "
        "Hover over any team to see its name and profile metrics."
    )

    fig = plot_team_profiles_pca_plotly(
        df_profiles,
        selected_teams=[home_team, away_team],
        title="Team tactical clusters",
    )
    st.plotly_chart(fig, use_container_width=True)

    # ------------------------------------------------------------------
    # Cluster summary
    # ------------------------------------------------------------------
    st.subheader("Average indicator values by cluster")
    st.caption(
        "This table summarizes the typical attacking profile of each tactical cluster."
    )
    st.dataframe(df_cluster_summary, use_container_width=True)


if __name__ == "__main__":
    main()