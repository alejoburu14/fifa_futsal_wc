"""
Utility functions and constants for processing game timelines and preparing
data for plotting.

This module provides:
    - constants tuned for futsal (halftime minute, smoothing tau, weights),
    - time parsing utilities that accept a range of common time formats from
        the API, and
    - functions to build attack-focused DataFrames used by plotting helpers.

Function notes:
    - `parse_time_to_seconds` is defensive: it accepts many textual patterns
        (e.g., "12:34", "PT12M34S", "12'34") because data coming from remote
        APIs is often inconsistent.
    - `ewma` implements a simple causal exponentially-weighted moving
        average used to smooth per-minute momentum curves.
"""

#Import libraries
from __future__ import annotations
from typing import Iterable, Tuple, Optional, Dict
import numpy as np
import pandas as pd
import re
from common.colors import pick_match_colors

# --- Constants ---
HALFTIME_MINUTE   = 20          # futsal standard halftime in minutes
SMOOTH_TAU_MIN    = 3.0         # EWMA time-constant (minutes) for smoothing lines
ATTEMPT_WEIGHT    = 1.0         # weight assigned to attempts
GOAL_WEIGHT       = 2.0         # weight assigned to goals (higher impact)
TOP_N_PLAYERS     = 8           # default top-N players to display in charts

# Whitelisted event descriptions considered 'attacking' for most plots
WHITELIST_ATTACK  = {"Attempt at Goal", "Goal!"}


# ---------- Small helpers ----------
def teams_ordered(series_or_iter: Iterable[str]) -> Tuple[str, str]:
    """Return a (team_a, team_b) tuple preserving the first two unique items."""
    uniq = []
    for t in series_or_iter:
        s = str(t)
        if s not in uniq:
            uniq.append(s)
        if len(uniq) == 2:
            break
    if len(uniq) == 1:
        uniq.append("(opponent)")
    return (uniq[0], uniq[1])


def parse_time_to_seconds(val) -> float:
    """
    Robust parsing to seconds.
    Accepts: 12, '12', '12:34', "12'34", '29"', 'PT12M34S', and messy variants with curly quotes.
    """
    # If value is missing or NaN, return 0 seconds.
    if pd.isna(val):
        return 0.0

    # Convert whatever we received into a trimmed string for parsing.
    s = str(val).strip()

    # Normalize common curly quotes to ASCII equivalents so regexes work.
    s = s.replace("’", "'").replace("′", "'").replace("“", '"').replace("”", '"')

    # 1) ISO-like duration format: e.g. 'PT12M34S' or 'PT34S'
    #    - Look for 'PT' prefix and 'S' suffix; extract minutes and seconds robustly.
    if s.startswith("PT") and s.endswith("S"):
        # 'm' matches minutes (PT<num>M) if present
        m = re.search(r'PT(\d+)M', s)
        # 'sec' matches the seconds after an 'M' (M<num>S)
        sec = re.search(r'M(\d+)S', s)
        if not m:  # e.g., 'PT34S' has only seconds
            sec_only = re.search(r'PT(\d+)S', s)
            return float(int(sec_only.group(1))) if sec_only else 0.0
        minutes = int(m.group(1))
        seconds = int(sec.group(1)) if sec else 0
        return float(minutes * 60 + seconds)

    # 2) 'mm:ss' or "mm'ss" style (also accept noisy characters)
    if ":" in s or "'" in s:
        # Split once on colon or apostrophe to keep any trailing junk ignored.
        parts = re.split(r"[:']", s, maxsplit=1)
        # Remove non-digits to be forgiving of extra characters.
        m_str = re.sub(r"\D", "", parts[0]) if parts else "0"
        sec_str = re.sub(r"\D", "", parts[1]) if len(parts) > 1 else "0"
        minutes = int(m_str) if m_str else 0
        seconds = int(sec_str) if sec_str else 0
        return float(minutes * 60 + seconds)

    # 3) Seconds-only patterns like '29"' or '29sec'
    if '"' in s or "sec" in s.lower():
        sec_str = re.sub(r"\D", "", s)
        return float(int(sec_str)) if sec_str else 0.0

    # 4) Pure integer -> treat as minutes (common shorthand)
    if re.fullmatch(r"\d+", s):
        return float(int(s) * 60)

    # 5) Last resort: extract any numbers found. If two numbers -> minute,second
    nums = re.findall(r"\d+", s)
    if len(nums) >= 2:
        return float(int(nums[0]) * 60 + int(nums[1]))
    if len(nums) == 1:
        return float(int(nums[0]) * 60)

    # If nothing matched, return 0 to keep downstream computations robust.
    return 0.0


def ewma(x: np.ndarray, dt_minutes: float = 1.0, tau_minutes: float = 3.0) -> np.ndarray:
    """Simple causal EWMA with time step dt and time constant tau (in minutes)."""
    # Return early for empty input (avoid index errors below)
    if len(x) == 0:
        return x

    # Compute the EWMA smoothing factor (alpha) from the time constant tau.
    # alpha in (0,1] where larger alpha means faster response to new values.
    alpha = 1.0 - np.exp(-dt_minutes / max(tau_minutes, 1e-9))

    # Prepare output array with float dtype and initialize with first value.
    y = np.zeros_like(x, dtype=float)
    y[0] = x[0]

    # Recursive causal update: y[i] = alpha * x[i] + (1-alpha) * y[i-1]
    # This implements a simple IIR low-pass filter that smooths short spikes.
    for i in range(1, len(x)):
        y[i] = alpha * x[i] + (1 - alpha) * y[i - 1]
    return y


def team_colors_map(match_row: pd.Series) -> Dict[str, str]:
    """
    Return {HomeName: home_color, AwayName: away_color} based on DB rule.
    """
    pal = pick_match_colors(
        home_name=match_row["HomeName"],
        away_name=match_row["AwayName"],
        home_id=str(match_row["HomeId"]),
        away_id=str(match_row["AwayId"]),
    )
    return {str(match_row["HomeName"]): pal.home_color,
            str(match_row["AwayName"]): pal.away_color}


# ---------- Data prep for charts ----------
def build_attack_df(df_events: pd.DataFrame, match_row: pd.Series, squads: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Filter to attacking actions (Attempt at Goal, Goal!) and add:
      - 'minute' (rounded int), 'sec' (seconds), 'label' (mm')
      - 'w' weights (Attempt=1, Goal=2)
      - 'TeamName' mapped from TeamId
      - 'PlayerName' merged from squads if available
    """
    # Work on a copy to avoid mutating the callers data
    df = df_events.copy()

    # Filter to only attacking actions (whitelist). This ensures downstream
    # charts focus on attempts and goals.
    df = df[df["Description"].isin(WHITELIST_ATTACK)].copy()

    # Map TeamId -> TeamName using the selected match_row values. Converting
    # TeamId to string makes the mapping robust to numeric vs string IDs.
    names = {
        str(match_row["HomeId"]): str(match_row["HomeName"]),
        str(match_row["AwayId"]): str(match_row["AwayName"]),
    }
    df["TeamId"] = df["TeamId"].astype(str)
    df["TeamName"] = df["TeamId"].map(names)

    # If squad/player information is provided, merge PlayerName into the
    # events DataFrame so charts can show player labels.
    if squads is not None and not squads.empty:
        # Require the expected columns before merging to avoid KeyError.
        if "PlayerId" in df.columns and "PlayerId" in squads.columns and "PlayerName" in squads.columns:
            df = df.merge(squads[["PlayerId", "PlayerName"]], on="PlayerId", how="left")
    if "PlayerName" not in df.columns:
        # Ensure the column exists for downstream code that expects it.
        df["PlayerName"] = ""

    # Compute time-related features used by plots:
    #  - 'sec' = absolute seconds parsed from the possibly messy 'MatchMinute'
    #  - 'minute' = rounded minute integer used for per-minute aggregation
    #  - 'label' = textual mm' label (e.g., "02'") for annotating goals
    df["sec"] = df["MatchMinute"].apply(parse_time_to_seconds)
    df["minute"] = (df["sec"] / 60.0).round().astype(int)
    df["label"] = (df["sec"] // 60).astype(int).map(lambda m: f"{int(m):02d}'")

    # Assign weights: goals count more than attempts. The lowercase comparison
    # protects against inconsistent capitalization in the data source.
    desc_l = df["Description"].astype(str).str.strip().str.lower()
    df["w"] = np.where(desc_l.isin({"goal", "goal!"}), GOAL_WEIGHT, ATTEMPT_WEIGHT)

    return df


def build_minute_matrix(df_attack: pd.DataFrame, match_row: pd.Series) -> pd.DataFrame:
    """
    Build a per-minute matrix with columns: minute, team_a, team_b (weighted sum).
    """
    teams = (str(match_row["HomeName"]), str(match_row["AwayName"]))

    # Baseline minutes range: futsal games are short, so 0..40 covers typical
    # playtime; adjust if you expect extra time.
    mins = pd.DataFrame({"minute": np.arange(0, 40 + 1, 1, dtype=int)})

    # Sum weights per minute and per team. This creates rows like
    # (minute, TeamName, w) with the aggregated weight.
    tmp = df_attack.groupby(["minute", "TeamName"], as_index=False)["w"].sum()

    # Merge Team A (home) values on the minutes baseline, leaving NaN where
    # a team had no events that minute.
    mat = mins.merge(
        tmp[tmp["TeamName"] == teams[0]][["minute", "w"]].rename(columns={"w": "team_a"}),
        on="minute",
        how="left",
    )

    # Merge Team B (away) values similarly and fill missing with zeros so
    # plotting code can operate without further checks.
    mat = mat.merge(
        tmp[tmp["TeamName"] == teams[1]][["minute", "w"]].rename(columns={"w": "team_b"}),
        on="minute",
        how="left",
    )
    mat[["team_a", "team_b"]] = mat[["team_a", "team_b"]].fillna(0.0)
    return mat


def build_goals_only(df_attack: pd.DataFrame) -> pd.DataFrame:
    """Return only goals with the prepared 'minute' and 'label' fields."""
    desc_l = df_attack["Description"].str.strip().str.lower()
    return df_attack.loc[desc_l.isin({"goal", "goal!"})].copy()
