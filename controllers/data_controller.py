import pandas as pd
from common.utils import get_matches, get_match_events, get_players_for_teams, process_timeline
from common.constants import COMPETITIONID, SEASONID, STAGEID

def load_matches() -> pd.DataFrame:
    return get_matches(SEASONID)

def load_match_datasets(match_row: pd.Series):
    events = get_match_events(COMPETITIONID, SEASONID, STAGEID, str(match_row["MatchId"]))
    squads = get_players_for_teams([str(match_row["HomeId"]), str(match_row["AwayId"])], COMPETITIONID, SEASONID)
    timeline = process_timeline(events, squads, match_row)
    return events, squads, timeline
