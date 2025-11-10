import pandas as pd
from common.utils import get_matches, get_match_events, get_players_for_teams, process_timeline
from common.constants import COMPETITIONID, SEASONID, STAGEID
from common.flags import get_team_flags, flags_by_teamid   # <-- NEW

def load_matches() -> pd.DataFrame:
    return get_matches(SEASONID)

def load_match_datasets(match_row: pd.Series):
    events = get_match_events(COMPETITIONID, SEASONID, STAGEID, str(match_row["MatchId"]))
    squads = get_players_for_teams([str(match_row["HomeId"]), str(match_row["AwayId"])], COMPETITIONID, SEASONID)
    timeline = process_timeline(events, squads, match_row)

    # --- Add flags (by TeamId) ---
    df_flags = get_team_flags()                # cached
    flag_map = flags_by_teamid(df_flags)
    timeline.insert(0, "Flag", timeline["TeamId"].map(flag_map))  # first column

    return events, squads, timeline

