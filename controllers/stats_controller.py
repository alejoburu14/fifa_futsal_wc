import pandas as pd
from common.constants import WHITELIST_EVENTS
from common.flags import get_team_flags, flags_by_teamid   # <-- NEW

def compute_event_stats(df_events: pd.DataFrame, match_row: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    team_names = {
        str(match_row["HomeId"]): str(match_row["HomeName"]),
        str(match_row["AwayId"]): str(match_row["AwayName"]),
    }

    # Flag mapping (by TeamId)
    df_flags = get_team_flags()
    flag_map = flags_by_teamid(df_flags)
    name_to_flag = {
        team_names[str(match_row["HomeId"])]: flag_map.get(str(match_row["HomeId"]), ""),
        team_names[str(match_row["AwayId"])]: flag_map.get(str(match_row["AwayId"]), ""),
    }

    df_all = df_events.copy()
    df_all["TeamId"] = df_all["TeamId"].astype(str)
    df_all["TeamName"] = df_all["TeamId"].map(team_names)
    df_all["Description"] = df_all["Description"].astype(str)

    # 1) Count of events by team (all events)
    counts = (
        df_all.groupby("TeamName", dropna=False)
        .size()
        .reset_index(name="TotalEvents")
        .sort_values("TotalEvents", ascending=False)
    )
    counts.insert(0, "Flag", counts["TeamName"].map(name_to_flag))  # add Flag first

    # 2) Distribution of selected events by team
    dist = df_all[df_all["Description"].isin(WHITELIST_EVENTS)]
    if dist.empty:
        dist_pivot = pd.DataFrame(
            {
                "TeamName": [team_names[str(match_row["HomeId"])], team_names[str(match_row["AwayId"])]],
                **{evt: [0, 0] for evt in WHITELIST_EVENTS},
            }
        )
    else:
        dist_pivot = (
            dist.pivot_table(
                index="TeamName", columns="Description", values="TeamId", aggfunc="count", fill_value=0
            )
            .reindex(columns=WHITELIST_EVENTS, fill_value=0)
            .reset_index()
        )
    dist_pivot.insert(0, "Flag", dist_pivot["TeamName"].map(name_to_flag))  # add Flag first

    # Ensure Home then Away ordering
    teams_order = [team_names[str(match_row["HomeId"])], team_names[str(match_row["AwayId"])]]
    counts = counts.set_index("TeamName").reindex(teams_order, fill_value=0).reset_index()
    dist_pivot = dist_pivot.set_index("TeamName").reindex(teams_order, fill_value=0).reset_index()

    return counts, dist_pivot
