import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from controllers.data_controller import load_match_datasets
from controllers.stats_controller import compute_event_stats
from controllers.auth_controller import logout_button
from common.ui import sidebar_header

from common.metrics import (
    build_attack_df, build_minute_matrix, build_goals_only,
    team_colors_map, HALFTIME_MINUTE, SMOOTH_TAU_MIN, TOP_N_PLAYERS
)
from common.plots import (
    plot_momentum, plot_smoothed, plot_top_players, plot_cumulative,
    plot_events_count_bar, plot_event_distribution_grouped
)

# ------------------------------------------------------------
# Page setup & consistent sidebar
# ------------------------------------------------------------
SMALL_FIGSIZE = (5.2, 2.0)  # <- compact size for all charts

st.set_page_config(page_title="Statistics", layout="wide")

def _ensure_auth():
    if not st.session_state.get("authenticated"):
        try:
            st.switch_page("main.py")
        except Exception:
            st.info("Please sign in on **Home** first.")
            st.stop()

def _ensure_match_selected():
    if "match_row" not in st.session_state or not st.session_state["match_row"]:
        st.info("Go to **Home** to select a match first.")
        st.stop()


def _swatch_row(home: str, away: str, color_home: str, color_away: str):
    """Render a colored swatch row just under a subheader."""
    sw = lambda c: f'<span style="display:inline-block;width:14px;height:14px;vertical-align:middle;background:{c};border:1px solid {"#000" if _is_light(c) else c};margin-right:6px"></span>'
    html = (
        f'{sw(color_home)} <b>{home}</b> &nbsp;&nbsp;VS&nbsp;&nbsp; '
        f'{sw(color_away)} <b>{away}</b>'
    )
    st.markdown(html, unsafe_allow_html=True)


def _is_light(hex_color: str) -> bool:
    """Perceived luminance to decide if we draw a dark border for very light (e.g., white)."""
    h = hex_color.strip().lstrip("#")
    try:
        r, g, b = int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0
    except Exception:
        return False
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return y >= 0.90


def main():
    _ensure_auth()
    sidebar_header(user=st.session_state.get("username"), show_custom_nav=True)
    logout_button()

    _ensure_match_selected()

    # Recover selection & load match data
    match_row = pd.Series(st.session_state["match_row"])
    events, squads, timeline = load_match_datasets(match_row)
    counts, dist = compute_event_stats(events, match_row)

    # Colors (from SQLite), keep consistent with Home if present
    colors_map = team_colors_map(match_row)  # {'HomeName': hex, 'AwayName': hex}
    sess_cols = st.session_state.get("team_colors")
    if isinstance(sess_cols, dict):
        colors_map[str(match_row["HomeName"])] = sess_cols.get("home", colors_map.get(str(match_row["HomeName"])))
        colors_map[str(match_row["AwayName"])] = sess_cols.get("away", colors_map.get(str(match_row["AwayName"])))
    home, away = str(match_row["HomeName"]), str(match_row["AwayName"])
    col_home, col_away = colors_map.get(home, "#777777"), colors_map.get(away, "#999999")

    st.header("Statistics")
    st.caption("Computed from the full timeline (before filtering attacking actions).")

    # ------------------------------------------------------------
    # TABLE + BAR: Events by team
    # ------------------------------------------------------------
    st.subheader("Eventos por equipo")
    st.dataframe(
        counts[["Flag", "TeamName", "TotalEvents"]],
        use_container_width=True,
        column_config={"Flag": st.column_config.ImageColumn(" ", width="small")},
    )

    #st.subheader("Events by team (bar)")
    _swatch_row(home, away, col_home, col_away)

    fig1, ax1 = plt.subplots(figsize=SMALL_FIGSIZE)
    plot_events_count_bar(
        counts=counts,
        match_row=match_row,
        colors_map={home: col_home, away: col_away},
        ax=ax1,
        ylabel="",
        title="",  # we show title via subheader
    )
    st.pyplot(fig1, use_container_width=False)

    # ------------------------------------------------------------
    # TABLE + GROUPED BARS: Event distribution
    # ------------------------------------------------------------
    st.subheader("Distribución de eventos por equipo")
    st.caption("Events: Attempt at Goal, Foul, Goal!, Assist, Corner")
    st.dataframe(
        dist[["Flag", "TeamName", "Attempt at Goal", "Foul", "Goal!", "Assist", "Corner"]],
        use_container_width=True,
        column_config={"Flag": st.column_config.ImageColumn(" ", width="small")},
    )

    #st.subheader("Event distribution by team (grouped)")
    _swatch_row(home, away, col_home, col_away)

    fig2, ax2 = plt.subplots(figsize=SMALL_FIGSIZE)
    plot_event_distribution_grouped(
        dist=dist,
        match_row=match_row,
        colors_map={home: col_home, away: col_away},
        ax=ax2,
        title="",  # title handled by subheader
    )
    st.pyplot(fig2, use_container_width=False)

    # ------------------------------------------------------------
    # Advanced plots: momentum, smoothed EWMA, top players, cumulative
    # ------------------------------------------------------------
    df_attack = build_attack_df(events, match_row, squads=squads)  # attempts+goals; minute/sec/weights
    minute_df = build_minute_matrix(df_attack, match_row)          # per-minute mirror
    goals_df  = build_goals_only(df_attack)                        # only goals for markers

    st.subheader("Momentum por minuto (Intentos=1, Gol=2)")
    _swatch_row(home, away, col_home, col_away)

    fig3, ax3 = plt.subplots(figsize=SMALL_FIGSIZE)
    plot_momentum(
        minute_df, (home, away), goals_df,
        halftime_minute=HALFTIME_MINUTE,
        colors_map={home: col_home, away: col_away},
        ax=ax3,
        show_legend=False,  # ensure no legend
    )
    st.pyplot(fig3, use_container_width=False)

    st.subheader(f"Momentum suavizado (EWMA, τ={SMOOTH_TAU_MIN:g} min)")
    _swatch_row(home, away, col_home, col_away)

    fig4, ax4 = plt.subplots(figsize=SMALL_FIGSIZE)
    plot_smoothed(
        minute_df, (home, away),
        tau_minutes=SMOOTH_TAU_MIN,
        colors_map={home: col_home, away: col_away},
        ax=ax4,
        legend_mode="none",
    )
    st.pyplot(fig4, use_container_width=False)

    st.subheader(f"Top {TOP_N_PLAYERS} jugadores en ataque")
    _swatch_row(home, away, col_home, col_away)

    fig5, ax5 = plt.subplots(figsize=SMALL_FIGSIZE)
    plot_top_players(
        df_attack,
        top_n=TOP_N_PLAYERS,
        colors_map={home: col_home, away: col_away},
        ax=ax5,
        show_legend=False,
    )
    st.pyplot(fig5, use_container_width=False)

    st.subheader("Ritmo de ataque acumulado")
    _swatch_row(home, away, col_home, col_away)

    fig6, ax6 = plt.subplots(figsize=SMALL_FIGSIZE)
    plot_cumulative(
        df_attack,
        colors_map={home: col_home, away: col_away},
        ax=ax6,
        show_legend=False,
    )
    st.pyplot(fig6, use_container_width=False)


if __name__ == "__main__":
    main()
