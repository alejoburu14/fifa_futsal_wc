"""
Data controller helpers that glue the common data-fetching utilities to
the Streamlit pages.

This module exposes two convenience functions used by pages:
    - `load_matches()` returns a DataFrame with the available matches.
    - `load_match_datasets(match_row)` returns raw events, squad/player info
        and a processed timeline DataFrame that the UI can show directly.

All heavy lifting (HTTP requests, caching, JSON -> DataFrame transformations)
is implemented in `common.utils`. This module simply composes those helpers
and adds the extra step of enriching the timeline with team flag URLs.
"""

import pandas as pd
from common.utils import get_matches, get_match_events, get_players_for_teams, process_timeline
from common.constants import COMPETITIONID, SEASONID, STAGEID
from common.flags import get_team_flags, flags_by_teamid   # helper to map TeamId -> flag URL

def load_matches() -> pd.DataFrame:
    return get_matches(SEASONID)

def load_match_datasets(match_row: pd.Series):
    # 1) Load raw datasets from the API (cached via helpers in `common.utils`).
    events = get_match_events(COMPETITIONID, SEASONID, STAGEID, str(match_row["MatchId"]))
    squads = get_players_for_teams([str(match_row["HomeId"]), str(match_row["AwayId"])], COMPETITIONID, SEASONID)

    # 2) Process timeline: normalize team/player names and keep attacking actions.
    timeline = process_timeline(events, squads, match_row)

    # 3) Enrich timeline with flag URLs. `get_team_flags` is cached, so this is
    #    a cheap lookup most of the time. `flags_by_teamid` turns the DataFrame
    #    into a simple mapping TeamId -> FlagURL which we then map into the
    #    timeline and insert as the first column for nicer table rendering.
    df_flags = get_team_flags()                # cached
    flag_map = flags_by_teamid(df_flags)
    timeline.insert(0, "Flag", timeline["TeamId"].map(flag_map))  # first column

    # Return the raw events and squads along with the prepared timeline used
    # directly by the UI.
    return events, squads, timeline

