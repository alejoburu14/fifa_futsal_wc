"""
Common utility functions for data fetching and lightweight helpers used by
multiple pages.

This module contains network helpers (a small requests.Session wrapper),
Streamlit-friendly cached wrappers around API calls (e.g., `get_matches`),
and UI convenience utilities such as `selectbox_with_placeholder` used to
render a selectbox that can start with a placeholder text.

The helper functions often return `pandas.DataFrame` objects because the
rest of the app uses pandas for tabular manipulations and plotting.
"""

# Import libraries
from __future__ import annotations
import os, re
from typing import Any, Dict, Iterable, List, Optional
import pandas as pd
import requests
import streamlit as st
from .constants import BASE_URL, LANG, USER_AGENT

def get_users() -> Dict[str, str]:
    try:
        if "auth" in st.secrets and "users" in st.secrets["auth"]:
            return dict(st.secrets["auth"]["users"])
    except Exception:
        pass
    return {os.getenv("APP_USER", "admin"): os.getenv("APP_PASSWORD", "admin")}

def safe_rerun() -> None:
    if hasattr(st, "rerun"): st.rerun()
    elif hasattr(st, "experimental_rerun"): st.experimental_rerun()
    else: st.stop()

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})

def fifa_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    url = f"{BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    qp = {"language": LANG}
    if params: qp.update(params)
    resp = SESSION.get(url, params=qp, timeout=(10,20))
    resp.raise_for_status()
    return resp.json()

def i18n_desc(lst: Any, default: str = "") -> str:
    if isinstance(lst, list) and lst:
        return str(lst[0].get("Description", default) or default)
    return default

@st.cache_data(ttl=3600, show_spinner=False)
def get_matches(season_id: str, count: int = 500) -> pd.DataFrame:
    # Fetch match calendar JSON from the API and transform into a DataFrame.
    # This function is cached with `st.cache_data` so repeated UI reruns within
    # the TTL will reuse the cached DataFrame instead of calling the network.
    data = fifa_get("/calendar/matches", params={"idSeason": season_id, "count": count})
    results = data.get("Results", []) or []

    rows = []
    for m in results:
        # Defensive extraction: JSON may not include 'Home' or 'Away' keys.
        home, away = (m.get("Home", {}) or {}), (m.get("Away", {}) or {})

        # Parse kickoff timestamp robustly; invalid/empty strings become NaT.
        local_date_str = m.get("LocalDate", "")
        ts = pd.to_datetime(local_date_str, errors="coerce")

        # Build a flat row with normalized field names used by the app.
        row = {
            "MatchId": m.get("IdMatch", ""),
            "StageName": i18n_desc(m.get("StageName")),
            "GroupName": i18n_desc(m.get("GroupName")),
            "HomeId": home.get("IdTeam", ""),
            "HomeName": home.get("ShortClubName", "") or home.get("TeamName", ""),
            "AwayId": away.get("IdTeam", ""),
            "AwayName": away.get("ShortClubName", "") or away.get("TeamName", ""),
            "KickoffTS": ts if pd.notnull(ts) else pd.NaT,
            "KickoffDate": ts.strftime("%Y-%m-%d") if pd.notnull(ts) else "",
        }
        # Friendly label used in selectboxes.
        row["MatchName"] = f'{row["HomeName"]} vs {row["AwayName"]}'
        rows.append(row)

    df = pd.DataFrame(rows)
    # Ensure KickoffTS is a proper datetime dtype after DataFrame construction.
    df["KickoffTS"] = pd.to_datetime(df["KickoffTS"], errors="coerce")
    return df

@st.cache_data(ttl=1800, show_spinner=False)
def get_match_events(competition_id: str, season_id: str, stage_id: str, match_id: str) -> pd.DataFrame:
    # Fetch the match timeline JSON and convert into a DataFrame of interest.
    data = fifa_get(f"/timelines/{competition_id}/{season_id}/{stage_id}/{match_id}")
    events = data.get("Event", []) or []

    # Build a lightweight events DataFrame containing only the fields the app
    # needs. Use defensive .get() with defaults to avoid KeyError on missing data.
    return pd.DataFrame({
        "TeamId": [e.get("IdTeam", "") for e in events],
        "PlayerId": [e.get("IdPlayer", "") for e in events],
        "Description": [i18n_desc(e.get("TypeLocalized")) for e in events],
        "MatchMinute": [e.get("MatchMinute", "") for e in events],
    })

@st.cache_data(ttl=86400, show_spinner=False)
def get_players_for_teams(team_ids: Iterable[str], competition_id: str, season_id: str) -> pd.DataFrame:
    # For each requested team, call the squad endpoint and extract a small
    # players table. Cache the result because squad rosters rarely change.
    rows = []
    for tid in team_ids:
        data = fifa_get(f"/teams/{tid}/squad", params={"idCompetition": competition_id, "idSeason": season_id})
        for p in data.get("Players", []) or []:
            rows.append({
                "TeamId": p.get("IdTeam", ""),
                "PlayerId": p.get("IdPlayer", ""),
                # Use i18n_desc to safely extract possibly-localized short name
                "PlayerName": i18n_desc(p.get("ShortName")),
            })
    return pd.DataFrame(rows)

def group_rank(name: str) -> int:
    if not name: return 99
    m = re.search(r"Group\s+([A-Z])", str(name), flags=re.I)
    if m:
        ch = m.group(1).upper()
        if "A" <= ch <= "Z":
            return ord(ch) - ord("A") + 1
    return 99

def stage_order(stage: str) -> int:
    s = (stage or "").lower()
    for pattern, val in [(r"round\s*of\s*16|sixteen",200),(r"quarter-?final",300),(r"semi-?final",400),(r"third|3rd",500),(r"final",600)]:
        if re.search(pattern, s): return val
    return 700

def sort_matches_for_select(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["__is_group"] = df["GroupName"].fillna("").str.contains(r"Group\s+[A-Z]", case=False, regex=True)
    df["__g_rank"], df["__s_rank"] = df["GroupName"].map(group_rank), df["StageName"].map(stage_order)
    df["__has_date"] = df["KickoffTS"].notna()
    df = df.sort_values(by=["__is_group","__g_rank","__s_rank","__has_date","KickoffTS","MatchName"],
                        ascending=[False,True,True,False,True,True], kind="mergesort")
    return df.drop(columns=["__is_group","__g_rank","__s_rank","__has_date"])

def selectbox_with_placeholder(
    label: str,
    options: List[str],
    key: Optional[str] = None,
    default_index: Optional[int] = None,
):
    """
    A selectbox that can start empty (placeholder) or preselect an item (default_index).
    - Uses a hidden label to avoid duplicate text under the title.
    - Works on older Streamlit as well.
    """
    try:
        # Newer Streamlit supports a `placeholder` argument; use it to show
        # the descriptive label while keeping the rendered label hidden.
        return st.selectbox(
            "",  # hide label text
            options=options,
            index=default_index,            # None -> placeholder shown; int -> preselect
            placeholder=label,
            label_visibility="collapsed",
            key=key,
        )
    except TypeError:
        # Older Streamlit versions do not accept `placeholder`. Fall back to
        # inserting a synthetic placeholder item at the front of the list.
        if default_index is None:
            placeholder = f"— {label} —"
            choice = st.selectbox(" ", options=[placeholder] + options, index=0, key=key)
            # Return None when the placeholder is selected so callers can
            # detect 'no selection' consistently.
            return None if choice == placeholder else choice
        else:
            # When a default index is provided, simply preselect that option
            # using the older Streamlit API.
            return st.selectbox(" ", options=options, index=default_index, key=key)

def process_timeline(df_events: pd.DataFrame, df_squads: pd.DataFrame, match_row: pd.Series) -> pd.DataFrame:
    """Return a cleaned timeline focused on attacking actions.

    Steps performed:
      1. Normalize `TeamId` to string and map it to the friendly team name using
         values from `match_row`.
      2. Merge player names from `df_squads` when available so the timeline
         includes `PlayerName` values for display.
      3. Filter to only focus on attacking actions (Attempt at Goal, Goal!).
      4. Select and order the final columns and sort by the raw `MatchMinute`
         string so the UI shows events in chronological order.
    """
    team_names = {
        str(match_row["HomeId"]): str(match_row["HomeName"]),
        str(match_row["AwayId"]): str(match_row["AwayName"]),
    }

    # Work on a copy to avoid mutating the original events DataFrame.
    df = df_events.copy()
    df["TeamId"] = df["TeamId"].astype(str)

    # Map TeamId to human readable TeamName using the selected match metadata.
    df["TeamName"] = df["TeamId"].map(team_names)

    # Merge player names when squads data is present so the timeline shows
    # who performed each action.
    if not df_squads.empty:
        df = df.merge(df_squads[["PlayerId", "PlayerName"]], on="PlayerId", how="left")

    # Filter to attacking actions only; this reduces noise for the timeline UI.
    df = df[df["Description"].isin(["Attempt at Goal", "Goal!"])]

    # Keep only the columns the UI needs and replace NaNs with empty strings
    # to avoid rendering issues in Streamlit's dataframe components.
    df = df[["TeamId", "TeamName", "Description", "MatchMinute", "PlayerName"]].fillna("")
    return df.sort_values(by=["MatchMinute"]).reset_index(drop=True)

