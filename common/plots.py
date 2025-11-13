# common/plots.py
from __future__ import annotations
from typing import Optional, Tuple, Dict

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Circle, Rectangle
import matplotlib.patheffects as pe

from common.metrics import (
    HALFTIME_MINUTE, SMOOTH_TAU_MIN, ATTEMPT_WEIGHT, GOAL_WEIGHT, TOP_N_PLAYERS,
    ewma, teams_ordered, team_colors_map
)

DEFAULT_FIGSIZE = (6.6, 2.6)  # more compact; tweak if you want even smaller

def _new_ax(ax=None):
    """Return a compact figure/axes when ax is None; otherwise reuse the axes."""
    if ax is None:
        fig, ax = plt.subplots(figsize=DEFAULT_FIGSIZE, constrained_layout=True)
    else:
        fig = ax.figure
    return fig, ax

# --- color helpers for outlines on light colors ---
def _hex_to_rgb01(hexs: str):
    h = hexs.strip().lstrip("#")
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return r, g, b

def _is_light_color(hexs: str, thr: float = 0.90) -> bool:
    """Perceived luminance threshold (Y) to decide if we need an outline."""
    try:
        r, g, b = _hex_to_rgb01(hexs)
        Y = 0.2126*r + 0.7152*g + 0.0722*b
        return Y >= thr
    except Exception:
        return False

def _edge_kw_for(hexs: str) -> dict:
    """Return edgecolor/linewidth kwargs for bars when color is very light."""
    return {"edgecolor": "black", "linewidth": 1.0} if _is_light_color(hexs) else {}

def _outline_line_if_light(line_obj, hexs: str):
    """Give a black stroke outline to very light lines so they’re visible."""
    if _is_light_color(hexs):
        lw = line_obj.get_linewidth()
        line_obj.set_path_effects([pe.Stroke(linewidth=lw + 1.5, foreground="black"), pe.Normal()])


# --- Events by team (simple two-bar chart) ---
def plot_events_count_bar(counts: pd.DataFrame,
                          match_row: pd.Series,
                          colors_map: Optional[Dict[str, str]] = None,
                          ax: Optional[plt.Axes] = None,
                          show_legend: bool = True,
                          ylabel: str = "",
                          title: str = "") -> plt.Axes:
    if ax is None:
        fig, ax = plt.subplots()
    colors = colors_map or {}

    home, away = str(match_row["HomeName"]), str(match_row["AwayName"])

    def _get_total(df, team):
        s = df.loc[df["TeamName"] == team, "TotalEvents"]
        return float(s.iloc[0]) if not s.empty else 0.0

    y_home = _get_total(counts, home)
    y_away = _get_total(counts, away)

    col_home = colors.get(home, "#777777")
    col_away = colors.get(away, "#999999")

    ax.bar([0], [y_home], color=col_home, label=home, **_edge_kw_for(col_home))
    ax.bar([1], [y_away], color=col_away, label=away, **_edge_kw_for(col_away))
    ax.set_xticks([0, 1], [home, away])
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.tick_params(axis="both", labelsize=6)

    return ax

# --- Event distribution by team (grouped bars) ---
def plot_event_distribution_grouped(dist: pd.DataFrame,
                                    match_row: pd.Series,
                                    events: Optional[list] = None,
                                    colors_map: Optional[Dict[str, str]] = None,
                                    ax: Optional[plt.Axes] = None,
                                    show_legend: bool = True,
                                    title: str = "") -> plt.Axes:
    if ax is None:
        fig, ax = plt.subplots()
    colors = colors_map or {}
    if events is None:
        events = ["Attempt at Goal", "Foul", "Goal!", "Assist", "Corner"]

    home, away = str(match_row["HomeName"]), str(match_row["AwayName"])
    for col in events:
        if col not in dist.columns:
            dist[col] = 0

    def _vals(team):
        row = dist.loc[dist["TeamName"] == team]
        if row.empty:
            return [0] * len(events)
        return row.iloc[0][events].tolist()

    home_vals = _vals(home)
    away_vals = _vals(away)

    x = np.arange(len(events), dtype=float)
    w = 0.42
    col_home = colors.get(home, "#777777")
    col_away = colors.get(away, "#999999")

    ax.bar(x - w/2, home_vals, width=w, color=col_home, align="center", label=home, **_edge_kw_for(col_home))
    ax.bar(x + w/2, away_vals, width=w, color=col_away, align="center", label=away, **_edge_kw_for(col_away))

    ax.set_xticks(x, events, rotation=0)
    ax.set_ylabel("")
    ax.set_title(title)
    ax.tick_params(axis="both", labelsize=6)

    return ax


# --- Momentum (mirror bars) ----------------
def plot_momentum(minute_df: pd.DataFrame,
                  teams: Tuple[str, str],
                  goals_df: pd.DataFrame,
                  halftime_minute: int = HALFTIME_MINUTE,
                  colors_map: Optional[Dict[str, str]] = None,
                  ax: Optional[plt.Axes] = None,
                  show_legend: bool = False) -> plt.Axes:
    colors = colors_map or {}
    fig, ax = _new_ax(ax)

    home, away = teams
    col_home = colors.get(home, "#777777")
    col_away = colors.get(away, "#999999")

    x  = minute_df["minute"].values
    up = minute_df["team_a"].values
    dn = -minute_df["team_b"].values

    ax.bar(x, up, width=0.8, color=col_home, **_edge_kw_for(col_home))
    ax.bar(x, dn, width=0.8, color=col_away, **_edge_kw_for(col_away))
    ax.axhline(0, color="black", linewidth=1)
    ax.axvline(halftime_minute, linestyle="--", linewidth=1, color="gray")

    ax.set_xlabel("Minute", fontsize=6); ax.set_ylabel("Weight per minute", fontsize=6)
    ax.tick_params(axis="both", labelsize=6)

    # labels: time only, very small; anti-overlap with pixel offsets; no icons
    if not goals_df.empty:
        y_span   = float(max(1.0, np.nanmax(np.abs(np.r_[up, dn]))))
        tip_pad  = 0.05 * y_span
        jitter_px = [-8, 0, 8]
        base_y_px = -1
        step_y_px = 6
        bump_px   = 6

        prev_minute = {home: None, away: None}
        for idx, team in enumerate((home, away)):
            sign = 1 if idx == 0 else -1
            col  = "team_a" if idx == 0 else "team_b"
            rows = goals_df.loc[goals_df["TeamName"] == team].sort_values("minute")

            for m, sub in rows.groupby("minute", sort=False):
                bar_val = float(minute_df.loc[minute_df["minute"] == m, col].values[0])
                tip_y   = sign * (abs(bar_val) + tip_pad)

                extra = bump_px if (prev_minute[team] is not None and (m - prev_minute[team]) <= 1) else 0
                prev_minute[team] = m

                for k, (_, r) in enumerate(sub.iterrows()):
                    # r['label'] is already "mm'"
                    txt = f"{r.get('label','')}".strip() + " (G)"
                    y_off = sign * (base_y_px + extra + k * step_y_px)
                    x_off = jitter_px[k % len(jitter_px)]
                    ax.annotate(
                        txt, xy=(float(m), tip_y), xycoords="data",
                        xytext=(x_off, y_off), textcoords="offset points",
                        ha="center", va="bottom" if sign > 0 else "top",
                        fontsize=3, color="black",
                        #bbox=dict(facecolor="white", edgecolor="0.7", alpha=0.85, pad=0.6),
                        clip_on=False,
                    )
    return ax


# --- Smoothed lines (EWMA) ----------------
def plot_smoothed(minute_df: pd.DataFrame,
                  teams: Tuple[str, str],
                  ax: Optional[plt.Axes] = None,
                  tau_minutes: float = SMOOTH_TAU_MIN,
                  colors_map: Optional[Dict[str, str]] = None,
                  legend_mode: str = "full") -> plt.Axes:
    colors = colors_map or {}
    if ax is None:
        fig, ax = plt.subplots()

    col_home = colors.get(teams[0], "#777777")
    col_away = colors.get(teams[1], "#999999")

    x  = minute_df["minute"].values.astype(float)
    a  = minute_df["team_a"].values.astype(float)
    b  = -minute_df["team_b"].values.astype(float)

    a_s = ewma(a, dt_minutes=1.0, tau_minutes=tau_minutes)
    b_s = ewma(b, dt_minutes=1.0, tau_minutes=tau_minutes)
    net = ewma(a - (-b), dt_minutes=1.0, tau_minutes=tau_minutes)

    la = ax.plot(x, a_s, color=col_home, linewidth=2, label=teams[0])[0]
    lb = ax.plot(x, b_s, color=col_away, linewidth=2, label=teams[1])[0]
    ln = ax.plot(x, net, color="gray", linestyle="--", linewidth=1, label="Net")[0]

    # add outlines to very light lines
    _outline_line_if_light(la, col_home)
    _outline_line_if_light(lb, col_away)

    ax.axhline(0, color="black", linewidth=1)
    ax.axvline(HALFTIME_MINUTE, linestyle="--", linewidth=1)
    ax.set_xlabel("Minute", fontsize=6); ax.set_ylabel("EWMA", fontsize=6)
    ax.tick_params(axis="both", labelsize=6)

    return ax



# --- Top players (horizontal bars) ----------------
def plot_top_players(df_goles: pd.DataFrame,
                     top_n: int = TOP_N_PLAYERS,
                     ax: Optional[plt.Axes] = None,
                     colors_map: Optional[Dict[str, str]] = None,
                     show_legend: bool = True,
                     legend_loc: str = "best") -> plt.Axes:
    if ax is None:
        fig, ax = plt.subplots()
    colors = colors_map or {}

    desc = df_goles["Description"].astype(str).str.strip().str.lower()
    df   = df_goles.copy()
    df["score"] = np.where(desc.isin({"goal", "goal!"}), GOAL_WEIGHT, ATTEMPT_WEIGHT)

    agg = (
        df.groupby(["PlayerName", "TeamName"], as_index=False)["score"]
          .sum()
          .sort_values("score", ascending=False)
          .head(top_n)
    )

    # Colors per team with outlines for light colors
    bar_colors = agg["TeamName"].map(lambda t: colors.get(t, "#888888"))
    bars = ax.barh(agg["PlayerName"], agg["score"], color=bar_colors)
    for patch, team in zip(bars, agg["TeamName"]):
        c = colors.get(team, "#888888")
        if _is_light_color(c):
            patch.set_edgecolor("black"); patch.set_linewidth(1.0)

    ax.invert_yaxis()
    ax.set_xlabel("Attacking participation (attempts + 2×goals)", fontsize=6)
    ax.tick_params(axis="both", labelsize=6)

    for i, v in enumerate(agg["score"]):
        ax.text(v + 0.1, i, f"{v:.0f}", va="center", fontsize=6)

    return ax



# --- Cumulative attack rate ----------------
def plot_cumulative(df_goles: pd.DataFrame,
                    ax: Optional[plt.Axes] = None,
                    colors_map: Optional[Dict[str, str]] = None,
                    show_legend: bool = True) -> plt.Axes:
    if ax is None: fig, ax = plt.subplots()
    colors = colors_map or {}
    teams = teams_ordered(df_goles["TeamName"])

    for team in teams:
        tmp = df_goles[df_goles["TeamName"] == team].sort_values("sec")
        x = tmp["sec"].values / 60.0
        y = tmp["w"].cumsum().values
        col = colors.get(team, "#888888")
        line = ax.step(x, y, where="post", label=team, color=col)[0]
        _outline_line_if_light(line, col)

    ax.set_xlabel("Minute", fontsize=6); ax.set_ylabel("Cumulative participation", fontsize=6)
    ax.tick_params(axis="both", labelsize=6)
    
    return ax
