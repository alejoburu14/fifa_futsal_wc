# pages/3_Infographic.py
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Patch
from io import BytesIO

# --- Header layout knobs (easy to tweak) ---
HEADER_POS = {
    "title_y":    0.990,  # main title
    "subtitle_y": 0.952,  # line under title
    "score_y":    0.912,  # score line
    "legend_y":   0.878,  # legend baseline
}

# Small, readable defaults (apply to figures created after this line)
plt.rcParams.update({
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 9,
    "figure.dpi": 110,
})

st.set_page_config(page_title="Infographic", layout="wide")

# Sidebar header (don’t hide page if the import fails)
try:
    from common.ui import sidebar_header
    sidebar_header(user=st.session_state.get("username"), show_custom_nav=True)
except Exception:
    pass


def _ensure_match_selected():
    if "match_row" not in st.session_state or not st.session_state["match_row"]:
        st.info("Go to **Home** and select a match first.")
        st.stop()


def _compute_score(events, home_id, away_id):
    desc = events["Description"].astype(str).str.strip().str.lower()
    g = events[desc.isin({"goal", "goal!"})].copy()
    g["TeamId"] = g["TeamId"].astype(str)
    home = int((g["TeamId"] == str(home_id)).sum())
    away = int((g["TeamId"] == str(away_id)).sum())
    return home, away


def _add_flag(fig: plt.Figure, url: str, left: float, top: float, width: float = 0.10):
    """Place a flag image at (left, top) in figure coords. Safe if download fails."""
    if not url:
        return
    try:
        from PIL import Image
        import requests
        from io import BytesIO as _BIO
        # Some servers dislike default UA – send a desktop UA
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                 "AppleWebKit/537.36 (KHTML, like Gecko) "
                                 "Chrome/120.0.0.0 Safari/537.36"}
        r = requests.get(url, timeout=8, headers=headers)
        r.raise_for_status()
        im = Image.open(_BIO(r.content)).convert("RGBA")
    except Exception:
        return
    w = width
    h = width * (im.size[1] / im.size[0])  # keep aspect ratio
    ax_img = fig.add_axes([left, top - h, w, h], anchor="NW")
    ax_img.imshow(im)
    ax_img.axis("off")


def _make_figure(match_row, events, df_attack, minute_df, goals_df, colors_map,
                 flag_left_url: str | None, flag_right_url: str | None) -> plt.Figure:
    # Lazy imports so import-time errors don’t hide the page
    from common.plots import plot_momentum, plot_smoothed, plot_top_players, plot_cumulative
    from common.metrics import HALFTIME_MINUTE, SMOOTH_TAU_MIN, TOP_N_PLAYERS

    home, away = str(match_row["HomeName"]), str(match_row["AwayName"])
    col_home = colors_map.get(home, "#777777")
    col_away = colors_map.get(away, "#999999")
    home_g, away_g = _compute_score(events, match_row["HomeId"], match_row["AwayId"])

    # Reserve generous top space so header/legend never overlap plots
    fig = plt.figure(figsize=(10.5, 6.9))
    fig.subplots_adjust(top=0.76)  # more margin than before
    gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.25)

    # 4 panels
    ax1 = fig.add_subplot(gs[0, 0])
    plot_momentum(minute_df, (home, away), goals_df,
                  halftime_minute=HALFTIME_MINUTE,
                  colors_map={home: col_home, away: col_away},
                  ax=ax1, show_legend=False)

    ax2 = fig.add_subplot(gs[0, 1])
    plot_smoothed(minute_df, (home, away),
                  tau_minutes=SMOOTH_TAU_MIN,
                  colors_map={home: col_home, away: col_away},
                  ax=ax2, legend_mode="none")

    ax3 = fig.add_subplot(gs[1, 0])
    plot_top_players(df_attack, top_n=TOP_N_PLAYERS,
                     colors_map={home: col_home, away: col_away},
                     ax=ax3, show_legend=False)

    ax4 = fig.add_subplot(gs[1, 1])
    plot_cumulative(df_attack,
                    colors_map={home: col_home, away: col_away},
                    ax=ax4, show_legend=False)

    # Header block (smaller fonts + extra spacing)
    title    = "Infographic — FIFA Futsal World Cup"
    subtitle = f'{match_row["StageName"]} • {match_row["GroupName"]} • {match_row.get("LocalDate", match_row.get("KickoffDate",""))}'
    scoreln  = f'Score: {home} {home_g} - {away_g} {away}'

    fig.suptitle(title, fontsize=13, y=HEADER_POS["title_y"])
    fig.text(0.5, HEADER_POS["subtitle_y"], subtitle, ha="center", va="center", fontsize=10)
    fig.text(0.5, HEADER_POS["score_y"],    scoreln,  ha="center", va="center", fontsize=10.5)

    # Compact legend below the score (use the same color patches)
    handles = [Patch(facecolor=col_home, label=home),
            Patch(facecolor=col_away, label=away)]
    fig.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, HEADER_POS["legend_y"]),
        ncol=2,
        frameon=False,
        prop={"size": 9},
    )

    # Flags in the extreme top corners
    _add_flag(fig, flag_left_url,  left=0.02,  top=HEADER_POS["title_y"], width=0.095)
    _add_flag(fig, flag_right_url, left=0.885, top=HEADER_POS["title_y"], width=0.095)


    return fig


def main():
    _ensure_match_selected()

    # Lazy imports
    from controllers.data_controller import load_match_datasets
    from common.colors import pick_match_colors
    from common.metrics import build_attack_df, build_minute_matrix, build_goals_only

    # Flags helper (support either function name)
    def _get_flags(match_row):
        try:
            from common.flags import get_flags_for_match
            return get_flags_for_match(match_row)
        except Exception:
            try:
                from common.flags import get_flag_url_by_team_id
                return (get_flag_url_by_team_id(str(match_row["HomeId"])),
                        get_flag_url_by_team_id(str(match_row["AwayId"])))
            except Exception:
                return "", ""

    match_row = st.session_state["match_row"]
    match_row = __import__("pandas").Series(match_row)

    events, squads, _ = load_match_datasets(match_row)
    df_attack = build_attack_df(events, match_row, squads=squads)
    minute_df = build_minute_matrix(df_attack, match_row)
    goals_df  = build_goals_only(df_attack)

    pal = pick_match_colors(
        home_name=str(match_row["HomeName"]),
        away_name=str(match_row["AwayName"]),
        home_id=str(match_row["HomeId"]),
        away_id=str(match_row["AwayId"]),
    )
    colors_map = {str(match_row["HomeName"]): pal.home_color,
                  str(match_row["AwayName"]): pal.away_color}

    home_flag, away_flag = _get_flags(match_row)

    st.header("Infographic")
    fig = _make_figure(match_row, events, df_attack, minute_df, goals_df,
                       colors_map, home_flag, away_flag)
    st.pyplot(fig, use_container_width=True)

    # Download PDF
    pdf = BytesIO()
    fig.savefig(pdf, format="pdf", bbox_inches="tight")
    st.download_button(
        "⬇️ Download PDF",
        data=pdf.getvalue(),
        file_name=f"infographic_{match_row['HomeName']}_vs_{match_row['AwayName']}.pdf",
        mime="application/pdf",
    )
    plt.close(fig)


if __name__ == "__main__":
    main()
