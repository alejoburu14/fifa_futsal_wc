# common/team_profiles.py
"""
Team attacking profile utilities.

This module rebuilds the clustering model directly from the app data layer,
using the same FIFA Futsal World Cup data already used by the Streamlit app.

Main responsibilities:
1. Load all matches
2. Load attacking events across all matches
3. Aggregate team-level tactical features
4. Fit K-Means clustering
5. Compute PCA coordinates for visualization
6. Return clean outputs for Streamlit pages
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from common.constants import COMPETITIONID, SEASONID, STAGEID
from common.ml_labels import CLUSTER_ORDER
from common.utils import get_match_events, get_matches

# Features used in clustering
PROFILE_FEATURES: List[str] = [
    "Attempts_per_Match",
    "Goals_per_Match",
    "Conversion_Rate",
    "Mean_Attack_Minute",
    "Early_Attack_Share",
    "Late_Attack_Share",
    "Attack_Variability",
]


def _extract_minute(series: pd.Series) -> pd.Series:
    """
    Convert MatchMinute strings into numeric minute values.

    Examples of possible raw values:
    - "12"
    - "12'"
    - '29"'
    - "40+1"

    We keep the first integer found and convert it to float.
    """
    return (
        series.astype(str)
        .str.extract(r"(\d+)")
        .fillna("0")
        .astype(float)
        .iloc[:, 0]
    )


@st.cache_data(ttl=3600, show_spinner=False)
def load_all_matches() -> pd.DataFrame:
    """
    Load all competition matches using the same helper as the rest of the app.
    """
    df_matches = get_matches(SEASONID).copy()
    if not df_matches.empty:
        # Keep IDs as strings for safe joins/maps
        for col in ["MatchId", "HomeId", "AwayId"]:
            if col in df_matches.columns:
                df_matches[col] = df_matches[col].astype(str)
    return df_matches


@st.cache_data(ttl=3600, show_spinner=False)
def load_all_attacking_events() -> pd.DataFrame:
    """
    Load attacking events for every match in the competition.

    Returns a DataFrame with:
    - MatchId
    - TeamId
    - TeamName
    - Description
    - MatchMinute
    - minute
    - is_goal
    """
    df_matches = load_all_matches()
    if df_matches.empty:
        return pd.DataFrame()

    # Build a lookup from (MatchId, TeamId) -> TeamName
    team_name_map: Dict[Tuple[str, str], str] = {}
    for _, row in df_matches.iterrows():
        team_name_map[(str(row["MatchId"]), str(row["HomeId"]))] = str(row["HomeName"])
        team_name_map[(str(row["MatchId"]), str(row["AwayId"]))] = str(row["AwayName"])

    all_events = []

    for _, row in df_matches.iterrows():
        match_id = str(row["MatchId"])
        try:
            df_events = get_match_events(
                COMPETITIONID,
                SEASONID,
                STAGEID,
                match_id,
            ).copy()
        except Exception:
            # If one match fails, we skip it and continue
            continue

        if df_events.empty:
            continue

        # Normalize key columns
        df_events["MatchId"] = match_id
        df_events["TeamId"] = df_events["TeamId"].astype(str)

        # Map team names using the match-specific dictionary
        df_events["TeamName"] = df_events.apply(
            lambda r: team_name_map.get((match_id, str(r["TeamId"])), ""),
            axis=1,
        )

        # Keep only attacking actions
        df_events = df_events[df_events["Description"].isin(["Attempt at Goal", "Goal!"])].copy()
        if df_events.empty:
            continue

        # Feature engineering at event level
        df_events["minute"] = _extract_minute(df_events["MatchMinute"])
        df_events["is_goal"] = (df_events["Description"] == "Goal!").astype(int)

        keep_cols = [
            "MatchId",
            "TeamId",
            "TeamName",
            "Description",
            "MatchMinute",
            "minute",
            "is_goal",
        ]
        all_events.append(df_events[keep_cols])

    if not all_events:
        return pd.DataFrame(columns=[
            "MatchId", "TeamId", "TeamName", "Description",
            "MatchMinute", "minute", "is_goal"
        ])

    return pd.concat(all_events, ignore_index=True)


def build_team_profile_features(
    df_matches: pd.DataFrame,
    df_attack: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build team-level tactical features for clustering.

    Feature logic:
    - Attempts_per_Match: attacking volume
    - Goals_per_Match: scoring output
    - Conversion_Rate: efficiency
    - Mean_Attack_Minute: average timing of attacks
    - Early_Attack_Share: share of attacks in first half
    - Late_Attack_Share: share of attacks in second half
    - Attack_Variability: how concentrated or dispersed attacks are over time
    """
    if df_matches.empty or df_attack.empty:
        return pd.DataFrame()

    # Count matches played by each team
    df_home = df_matches[["HomeId", "HomeName"]].copy()
    df_home.columns = ["TeamId", "TeamName"]

    df_away = df_matches[["AwayId", "AwayName"]].copy()
    df_away.columns = ["TeamId", "TeamName"]

    df_teams_matches = pd.concat([df_home, df_away], ignore_index=True)
    df_teams_matches["TeamId"] = df_teams_matches["TeamId"].astype(str)

    matches_per_team = (
        df_teams_matches.groupby(["TeamId", "TeamName"])
        .size()
        .reset_index(name="Matches_Played")
    )

    # Aggregate attacking event features
    team_stats = (
        df_attack.groupby(["TeamId", "TeamName"])
        .agg(
            Total_Attempts=("Description", "count"),
            Total_Goals=("is_goal", "sum"),
            Mean_Attack_Minute=("minute", "mean"),
            Attack_Variability=("minute", "std"),
        )
        .reset_index()
    )

    # Early vs late attacking share
    early_counts = (
        df_attack[df_attack["minute"] <= 20]
        .groupby(["TeamId", "TeamName"])
        .size()
        .reset_index(name="Early_Attacks")
    )

    late_counts = (
        df_attack[df_attack["minute"] > 20]
        .groupby(["TeamId", "TeamName"])
        .size()
        .reset_index(name="Late_Attacks")
    )

    # Merge all pieces
    df_features = team_stats.merge(matches_per_team, on=["TeamId", "TeamName"], how="left")
    df_features = df_features.merge(early_counts, on=["TeamId", "TeamName"], how="left")
    df_features = df_features.merge(late_counts, on=["TeamId", "TeamName"], how="left")

    # Fill missing counts/std
    df_features["Early_Attacks"] = df_features["Early_Attacks"].fillna(0)
    df_features["Late_Attacks"] = df_features["Late_Attacks"].fillna(0)
    df_features["Attack_Variability"] = df_features["Attack_Variability"].fillna(0)

    # Normalize by matches played
    df_features["Attempts_per_Match"] = (
        df_features["Total_Attempts"] / df_features["Matches_Played"]
    )
    df_features["Goals_per_Match"] = (
        df_features["Total_Goals"] / df_features["Matches_Played"]
    )
    df_features["Conversion_Rate"] = (
        df_features["Total_Goals"] / df_features["Total_Attempts"]
    ).fillna(0)

    # Temporal shares
    df_features["Early_Attack_Share"] = (
        df_features["Early_Attacks"] / df_features["Total_Attempts"]
    ).fillna(0)
    df_features["Late_Attack_Share"] = (
        df_features["Late_Attacks"] / df_features["Total_Attempts"]
    ).fillna(0)

    return df_features


def _assign_cluster_labels(df_profiles: pd.DataFrame) -> pd.DataFrame:
    """
    Convert raw K-Means cluster IDs into stable tactical labels.

    Because K-Means cluster numbers are arbitrary, we remap them to meaningful
    names based on cluster averages:

    1. Highest Attempts_per_Match -> High-Intensity Attackers
    2. Among the remaining clusters, highest Conversion_Rate -> Efficient Finishers
    3. Remaining cluster -> Low-Intensity Teams
    """
    cluster_summary = (
        df_profiles.groupby("ClusterRaw")[["Attempts_per_Match", "Conversion_Rate"]]
        .mean()
        .reset_index()
    )

    # 1) Identify the highest-intensity cluster
    high_intensity_raw = cluster_summary.loc[
        cluster_summary["Attempts_per_Match"].idxmax(), "ClusterRaw"
    ]

    remaining = cluster_summary[cluster_summary["ClusterRaw"] != high_intensity_raw].copy()

    # 2) Among remaining clusters, highest conversion = efficient
    efficient_raw = remaining.loc[
        remaining["Conversion_Rate"].idxmax(), "ClusterRaw"
    ]

    # 3) Remaining one = low-intensity
    low_raw = remaining[remaining["ClusterRaw"] != efficient_raw]["ClusterRaw"].iloc[0]

    raw_to_label = {
        high_intensity_raw: "High-Intensity Attackers",
        efficient_raw: "Efficient Finishers",
        low_raw: "Low-Intensity Teams",
    }

    label_to_id = {label: i for i, label in enumerate(CLUSTER_ORDER)}

    df_profiles = df_profiles.copy()
    df_profiles["ClusterLabel"] = df_profiles["ClusterRaw"].map(raw_to_label)
    df_profiles["ClusterId"] = df_profiles["ClusterLabel"].map(label_to_id)

    return df_profiles


@st.cache_data(ttl=3600, show_spinner=False)
def compute_team_profile_outputs(n_clusters: int = 3):
    """
    End-to-end pipeline for team tactical profiles.

    Returns:
    - df_profiles: team-level table with metrics, cluster, and PCA coordinates
    - df_cluster_summary: average metrics per cluster
    - df_attack: attacking event-level data (useful for future pages)
    """
    df_matches = load_all_matches()
    df_attack = load_all_attacking_events()
    df_features = build_team_profile_features(df_matches, df_attack)

    if df_features.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    X = df_features[PROFILE_FEATURES].fillna(0)

    # Scale features because clustering is distance-based
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # K-Means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    raw_labels = kmeans.fit_predict(X_scaled)

    df_profiles = df_features.copy()
    df_profiles["ClusterRaw"] = raw_labels

    # Stable cluster labels
    df_profiles = _assign_cluster_labels(df_profiles)

    # PCA for 2D visualization
    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(X_scaled)

    df_profiles["PC1"] = coords[:, 0]
    df_profiles["PC2"] = coords[:, 1]

    # Summary table by cluster
    df_cluster_summary = (
        df_profiles.groupby(["ClusterId", "ClusterLabel"])[PROFILE_FEATURES]
        .mean()
        .reset_index()
        .sort_values(["ClusterId"])
        .reset_index(drop=True)
    )

    # Sort team table for display
    df_profiles = df_profiles.sort_values(["ClusterId", "TeamName"]).reset_index(drop=True)

    return df_profiles, df_cluster_summary, df_attack


@st.cache_data(ttl=3600, show_spinner=False)
def get_team_profile_map() -> Dict[str, str]:
    """
    Convenient lookup used by other pages:
    TeamName -> ClusterLabel
    """
    df_profiles, _, _ = compute_team_profile_outputs()
    if df_profiles.empty:
        return {}
    return dict(zip(df_profiles["TeamName"], df_profiles["ClusterLabel"]))

# common/team_profiles.py
import matplotlib.pyplot as plt
from common.ml_labels import CLUSTER_COLORS, CLUSTER_ORDER


def plot_team_profiles_pca(
    df_profiles: pd.DataFrame,
    selected_teams: list[str] | None = None,
    ax=None,
    title: str = "Team tactical clusters",
):
    """
    Plot the PCA cluster chart and optionally highlight selected teams.

    Parameters
    ----------
    df_profiles : pd.DataFrame
        Output from compute_team_profile_outputs().
    selected_teams : list[str] | None
        Team names to highlight.
    ax : matplotlib axis | None
        Existing axis to draw into. If None, a new figure is created.
    title : str
        Chart title.

    Returns
    -------
    ax : matplotlib axis
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))

    selected_teams = selected_teams or []

    # 1) Base scatter per cluster
    for label in CLUSTER_ORDER:
        tmp = df_profiles[df_profiles["ClusterLabel"] == label]
        ax.scatter(
            tmp["PC1"],
            tmp["PC2"],
            label=label,
            color=CLUSTER_COLORS.get(label),
            s=70,
            alpha=0.75,
        )

    # 2) Labels for all teams (slightly above the point)
    for _, r in df_profiles.iterrows():
        ax.annotate(
            r["TeamName"],
            (r["PC1"], r["PC2"]),
            xytext=(0, 8),              # puts label above the point
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=5,
            alpha=0.7,
        )

    # 3) Highlight selected teams
    for team in selected_teams:
        row = df_profiles[df_profiles["TeamName"] == team]
        if row.empty:
            continue
        row = row.iloc[0]

        ax.scatter(
            row["PC1"],
            row["PC2"],
            s=220,
            color=CLUSTER_COLORS.get(row["ClusterLabel"], "#000000"),
            edgecolor="black",
            linewidth=1,
            zorder=5,
        )

    ax.set_title(title)
    ax.set_xlabel("Principal Component 1", fontsize=6)
    ax.set_ylabel("Principal Component 2", fontsize=6)
    ax.grid(alpha=0.2)
    ax.tick_params(labelsize=6)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.15), ncol=3)
    return ax