from __future__ import annotations
from typing import Dict, Optional

import pandas as pd
import streamlit as st

from common.constants import BASE_URL, SEASONID
from common.utils import fifa_get

# Square flag base (e.g., .../flags-sq-4/ARG)
FLAG_BASE = f"{BASE_URL}/picture/flags-sq-4"


@st.cache_data(ttl=86400, show_spinner=False)
def get_team_flags(season_id: str = SEASONID) -> pd.DataFrame:
    """
    Fetch teams for the given season and build a DataFrame with flag URLs.

    Returns:
      TeamId (str), TeamName (str), AbbreviationName (str), Confederation (str), Flag (str URL)
    """
    data = fifa_get(f"/competitions/teams/{season_id}")   # language handled by fifa_get
    results = data.get("Results", []) or []

    rows = []
    for t in results:
        abbr = t.get("Abbreviation", "") or ""
        team_name = t.get("ShortClubName", "") or t.get("TeamName", "") or ""
        rows.append(
            {
                "TeamId": str(t.get("IdTeam", "")),
                "TeamName": team_name,
                "AbbreviationName": abbr,
                "Confederation": str(t.get("IdConfederation", "")),
                "Flag": f"{FLAG_BASE}/{abbr}" if abbr else "",
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        for c in ["TeamId", "TeamName", "AbbreviationName", "Confederation", "Flag"]:
            df[c] = df[c].astype(str)
    return df


def flags_by_teamid(df_flags: pd.DataFrame) -> Dict[str, str]:
    """Return a {TeamId -> FlagURL} mapping."""
    if df_flags.empty:
        return {}
    return dict(zip(df_flags["TeamId"].astype(str), df_flags["Flag"]))


def flag_url_from_abbr(abbreviation: Optional[str]) -> str:
    """Build a single flag URL from a code like 'ARG'."""
    return f"{FLAG_BASE}/{abbreviation}" if abbreviation else ""
