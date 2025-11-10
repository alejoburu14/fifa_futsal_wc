# common/metrics.py
from __future__ import annotations
from typing import Iterable, Tuple, Optional, Dict
import numpy as np
import pandas as pd
import re
from common.colors import pick_match_colors

# --- Constants you can tweak ---
HALFTIME_MINUTE   = 20          # futsal
SMOOTH_TAU_MIN    = 3.0         # EWMA tau (minutes)
ATTEMPT_WEIGHT    = 1.0
GOAL_WEIGHT       = 2.0
TOP_N_PLAYERS     = 8

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
    if pd.isna(val):
        return 0.0
    s = str(val).strip()

    # Normalize curly quotes to ASCII
    s = s.replace("’", "'").replace("′", "'").replace("“", '"').replace("”", '"')

    # 1) ISO-ish PTxxMxxS
    if s.startswith("PT") and s.endswith("S"):
        # Extract M and S robustly
        m = re.search(r'PT(\d+)M', s)
        sec = re.search(r'M(\d+)S', s)
        if not m:  # e.g., PT34S
            sec_only = re.search(r'PT(\d+)S', s)
            return float(int(sec_only.group(1))) if sec_only else 0.0
        minutes = int(m.group(1))
        seconds = int(sec.group(1)) if sec else 0
        return float(minutes * 60 + seconds)

    # 2) mm:ss or mm'ss (allow extra junk around seconds)
    if ":" in s or "'" in s:
        parts = re.split(r"[:']", s, maxsplit=1)
        m_str = re.sub(r"\D", "", parts[0]) if parts else "0"
        sec_str = re.sub(r"\D", "", parts[1]) if len(parts) > 1 else "0"
        minutes = int(m_str) if m_str else 0
        seconds = int(sec_str) if sec_str else 0
        return float(minutes * 60 + seconds)

    # 3) seconds only pattern like 29" or 29sec
    if '"' in s or "sec" in s.lower():
        sec_str = re.sub(r"\D", "", s)
        return float(int(sec_str)) if sec_str else 0.0

    # 4) pure integer minutes
    if re.fullmatch(r"\d+", s):
        return float(int(s) * 60)

    # 5) last resort: extract digits; if two numbers => mm ss; if one => treat as minutes
    nums = re.findall(r"\d+", s)
    if len(nums) >= 2:
        return float(int(nums[0]) * 60 + int(nums[1]))
    if len(nums) == 1:
        return float(int(nums[0]) * 60)

    # fallback
    return 0.0


def ewma(x: np.ndarray, dt_minutes: float = 1.0, tau_minutes: float = 3.0) -> np.ndarray:
    """Simple causal EWMA with time step dt and time constant tau (in minutes)."""
    if len(x) == 0:
        return x
    alpha = 1.0 - np.exp(-dt_minutes / max(tau_minutes, 1e-9))
    y = np.zeros_like(x, dtype=float)
    y[0] = x[0]
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
    df = df_events.copy()
    df = df[df["Description"].isin(WHITELIST_ATTACK)].copy()

    # TeamName by TeamId
    names = {
        str(match_row["HomeId"]): str(match_row["HomeName"]),
        str(match_row["AwayId"]): str(match_row["AwayName"]),
    }
    df["TeamId"]   = df["TeamId"].astype(str)
    df["TeamName"] = df["TeamId"].map(names)

    # Merge player names if squads provided
    if squads is not None and not squads.empty:
        # Expect columns: PlayerId, PlayerName
        if "PlayerId" in df.columns and "PlayerId" in squads.columns and "PlayerName" in squads.columns:
            df = df.merge(squads[["PlayerId", "PlayerName"]], on="PlayerId", how="left")
    if "PlayerName" not in df.columns:
        df["PlayerName"] = ""

    # Time features
    df["sec"]    = df["MatchMinute"].apply(parse_time_to_seconds)
    df["minute"] = (df["sec"] / 60.0).round().astype(int)
    df["label"]  = (df["sec"] // 60).astype(int).map(lambda m: f"{int(m):02d}'")

    # Weights
    desc_l = df["Description"].astype(str).str.strip().str.lower()
    df["w"] = np.where(desc_l.isin({"goal", "goal!"}), GOAL_WEIGHT, ATTEMPT_WEIGHT)

    return df


def build_minute_matrix(df_attack: pd.DataFrame, match_row: pd.Series) -> pd.DataFrame:
    """
    Build a per-minute matrix with columns: minute, team_a, team_b (weighted sum).
    """
    teams = (str(match_row["HomeName"]), str(match_row["AwayName"]))

    mins = pd.DataFrame({"minute": np.arange(0, 40 + 1, 1, dtype=int)})
    tmp = df_attack.groupby(["minute", "TeamName"], as_index=False)["w"].sum()
    mat = mins.merge(tmp[tmp["TeamName"] == teams[0]][["minute", "w"]]
                     .rename(columns={"w": "team_a"}), on="minute", how="left")
    mat = mat.merge(tmp[tmp["TeamName"] == teams[1]][["minute", "w"]]
                    .rename(columns={"w": "team_b"}), on="minute", how="left")
    mat[["team_a", "team_b"]] = mat[["team_a", "team_b"]].fillna(0.0)
    return mat


def build_goals_only(df_attack: pd.DataFrame) -> pd.DataFrame:
    """Return only goals with the prepared 'minute' and 'label' fields."""
    desc_l = df_attack["Description"].str.strip().str.lower()
    return df_attack.loc[desc_l.isin({"goal", "goal!"})].copy()
