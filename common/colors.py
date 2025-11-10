# common/colors.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import colorsys
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from common.flags import get_team_flags  # used to map TeamId -> FIFA Abbreviation
from common.constants import BASE_URL, SEASONID  # BASE_URL only used to keep consistency

# DB location: <project_root>/assets/team_colors.db
DB_PATH = Path(__file__).resolve().parents[1] / "assets" / "team_colors.db"


# -------------------- SQLite loader --------------------
@st.cache_data(ttl=86400, show_spinner=False)
def load_colors_db(db_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load team colors from the SQLite DB.
    Expects a table team_colors(name TEXT, abbr TEXT, home_color TEXT, away_color TEXT).
    Returns a DataFrame with normalized lookup keys.
    """
    p = Path(db_path) if db_path else DB_PATH
    if not p.exists():
        return pd.DataFrame(columns=["name", "abbr", "home_color", "away_color", "key_name", "key_abbr"])

    con = sqlite3.connect(p)
    try:
        df = pd.read_sql_query(
            "SELECT name, abbr, home_color, away_color FROM team_colors",
            con
        )
    finally:
        con.close()

    for c in ["name", "abbr", "home_color", "away_color"]:
        df[c] = df[c].astype(str)

    # normalized keys for robust lookups
    df["key_name"] = df["name"].str.upper().str.strip()
    df["key_abbr"] = df["abbr"].str.upper().str.strip()
    return df


def db_lookup_palette(df_db: pd.DataFrame, name: Optional[str], abbr: Optional[str]) -> Optional[Dict[str, str]]:
    """Try abbr first, then full name. Return {'home':hex,'away':hex} or None."""
    if df_db is None or df_db.empty:
        return None
    if abbr:
        hit = df_db.loc[df_db["key_abbr"] == str(abbr).upper().strip()]
        if not hit.empty:
            row = hit.iloc[0]
            return {"home": row["home_color"], "away": row["away_color"]}
    if name:
        hit = df_db.loc[df_db["key_name"] == str(name).upper().strip()]
        if not hit.empty:
            row = hit.iloc[0]
            return {"home": row["home_color"], "away": row["away_color"]}
    return None


# -------------------- Simple color math (for fallback & similarity) --------------------
def _hex_to_rgb(hexs: str) -> Tuple[float, float, float]:
    h = hexs.strip().lstrip("#")
    return int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0


def _rgb_to_lab(r: float, g: float, b: float) -> Tuple[float, float, float]:
    # sRGB -> XYZ -> Lab (D65)
    def f(u): return (u / 12.92) if u <= 0.04045 else (((u + 0.055) / 1.055) ** 2.4)
    r, g, b = f(r), f(g), f(b)
    X = r * 0.4124 + g * 0.3576 + b * 0.1805
    Y = r * 0.2126 + g * 0.7152 + b * 0.0722
    Z = r * 0.0193 + g * 0.1192 + b * 0.9505
    Xn, Yn, Zn = 0.95047, 1.00000, 1.08883

    def gfun(t): return t ** (1 / 3) if t > 0.008856 else (7.787 * t + 16 / 116)
    fx, fy, fz = gfun(X / Xn), gfun(Y / Yn), gfun(Z / Zn)
    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b2 = 200 * (fy - fz)
    return L, a, b2


def _delta_e76(c1: str, c2: str) -> float:
    r1, g1, b1 = _hex_to_rgb(c1); L1, a1, b1_ = _rgb_to_lab(r1, g1, b1)
    r2, g2, b2 = _hex_to_rgb(c2); L2, a2, b2_ = _rgb_to_lab(r2, g2, b2)
    return ((L1 - L2) ** 2 + (a1 - a2) ** 2 + (b1_ - b2_) ** 2) ** 0.5


def _lighten_or_darken(hexs: str, factor: float = 0.15) -> str:
    """Positive factor lightens, negative darkens."""
    r, g, b = _hex_to_rgb(hexs)
    if factor >= 0:
        r += (1 - r) * factor; g += (1 - g) * factor; b += (1 - b) * factor
    else:
        r *= (1 + factor); g *= (1 + factor); b *= (1 + factor)
    return "#{:02X}{:02X}{:02X}".format(int(r * 255), int(g * 255), int(b * 255))


def _similar(c1: str, c2: str, delta: float = 20.0) -> bool:
    """Rough similarity check using ΔE76; ~10–20 is 'perceptible'."""
    try:
        return _delta_e76(c1, c2) < delta
    except Exception:
        return c1.lower() == c2.lower()


# -------------------- Public API --------------------
@dataclass(frozen=True)
class MatchPalette:
    home_color: str
    away_color: str


def pick_match_colors(
    home_name: str,
    away_name: str,
    home_id: Optional[str] = None,
    away_id: Optional[str] = None,
) -> MatchPalette:
    """
    Choose (home_color, away_color) from the SQLite DB.
    Rule:
      - Use Home.home vs Away.away from DB.
      - If similar, use Away.home.
      - If still similar, darken away slightly.
    Falls back to deterministic colors if a team is not found in the DB.
    """
    # Try to fetch FIFA abbreviations (ARG, BRA, …) from the cached flags
    abbr_home = abbr_away = None
    try:
        df_flags: pd.DataFrame = get_team_flags()
        if home_id is not None:
            hit = df_flags.loc[df_flags["TeamId"].astype(str) == str(home_id)]
            if not hit.empty:
                abbr_home = hit.iloc[0]["AbbreviationName"]
        if away_id is not None:
            hit = df_flags.loc[df_flags["TeamId"].astype(str) == str(away_id)]
            if not hit.empty:
                abbr_away = hit.iloc[0]["AbbreviationName"]
    except Exception:
        pass

    df_db = load_colors_db()

    # Look up palettes in DB (abbr first, then name)
    pal_home = db_lookup_palette(df_db, home_name, abbr_home)
    pal_away = db_lookup_palette(df_db, away_name, abbr_away)

    # Deterministic, nice-looking fallback if a team isn't in the DB
    if pal_home is None:
        h = (hash(home_name or "") % 360) / 360.0
        r, g, b = colorsys.hsv_to_rgb(h, 0.65, 0.95)
        base = "#{:02X}{:02X}{:02X}".format(int(r * 255), int(g * 255), int(b * 255))
        pal_home = {"home": base, "away": _lighten_or_darken(base, -0.25)}
    if pal_away is None:
        h = (hash(away_name or "") % 360) / 360.0
        r, g, b = colorsys.hsv_to_rgb(h, 0.65, 0.95)
        base = "#{:02X}{:02X}{:02X}".format(int(r * 255), int(g * 255), int(b * 255))
        pal_away = {"home": base, "away": _lighten_or_darken(base, -0.25)}

    c_home = pal_home["home"]
    c_away = pal_away["away"]

    # Similarity rule: if clash, switch to away's home; if still close, darken
    if _similar(c_home, c_away):
        c_away = pal_away["home"]
    if _similar(c_home, c_away):
        c_away = _lighten_or_darken(c_away, -0.25)

    return MatchPalette(home_color=c_home, away_color=c_away)
