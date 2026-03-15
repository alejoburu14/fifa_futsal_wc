# pages/3_Team_Profiles.py
from __future__ import annotations

import pandas as pd
import streamlit as st

from common.ml_labels import CLUSTER_DESCRIPTIONS
from common.team_profiles import compute_team_profile_outputs, plot_team_profiles_pca
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
            return (get_flag_url_by_team_id(str(match_row["HomeId"])),
                    get_flag_url_by_team_id(str(match_row["AwayId"])))
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
        df_profiles, df_cluster_summary, _ = compute_team_profile_outputs()

    if df_profiles.empty:
        st.warning("Team profile data could not be computed.")
        st.stop()

    st.title("⚽ Team Profiles")
    st.caption(
        "This page shows tactical team profiles."
    )

    # ------------------------------------------------------------------
    # Cluster definitions
    # ------------------------------------------------------------------
    st.subheader("Cluster definitions")
    for label, desc in CLUSTER_DESCRIPTIONS.items():
        st.markdown(f"**{label}** — {desc}")

    # ------------------------------------------------------------------
    # Comparison table for the 2 selected teams
    # ------------------------------------------------------------------
    st.markdown(f"### <img src='{home_flag}' width='35' height='35' style='vertical-align:middle;'> {home_team} vs {away_team} <img src='{away_flag}' width='35' height='35' style='vertical-align:middle;'>", unsafe_allow_html=True)

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

    # Build comparison table with indicators as rows and teams as columns
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
                    row_data[team] = f"{val:.2%}"
                elif metric_col == "ClusterLabel":
                    row_data[team] = str(val)
                else:
                    row_data[team] = f"{val:.2f}"
        comparison_rows.append(row_data)

    df_compare = pd.DataFrame(comparison_rows)

    st.dataframe(df_compare, use_container_width=True, hide_index=True)

    st.markdown("**Indicator definitions**")
    defs = _metric_definitions()
    for _, r in defs.iterrows():
        st.markdown(f"<small>- **{r['Indicator']}**: {r['Meaning']}</small>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Team -> Cluster table (alphabetical, highlight the 2 selected teams)
    # ------------------------------------------------------------------
    st.subheader("Team → Cluster table")

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
    # PCA chart (highlight the 2 selected teams)
    # ------------------------------------------------------------------
    st.subheader("2D cluster visualization (PCA)")
    st.caption(
        "PCA is used only for visualization. It reduces the feature space to two dimensions "
        "so the cluster structure is easier to interpret."
    )

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 6))
    plot_team_profiles_pca(
        df_profiles,
        selected_teams=[home_team, away_team],
        ax=ax,
        title=f"Team tactical clusters — {home_team} vs {away_team}",
    )
    st.pyplot(fig)

    # ------------------------------------------------------------------
    # Cluster summary
    # ------------------------------------------------------------------
    st.subheader("Average profile by cluster")
    st.dataframe(df_cluster_summary, use_container_width=True)


if __name__ == "__main__":
    main()