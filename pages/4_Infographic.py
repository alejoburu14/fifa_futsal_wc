"""
Infographic page: compose several plots into a single figure for download.

This page builds a composite matplotlib figure (5 panels) that summarizes a
selected match. It uses the plotting helpers from `common.plots` and
resources such as team flags to decorate the infographic. The module keeps
network and image loading inside try/except blocks so that a missing flag
image does not break the page.
"""

# Import libraries
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Patch
from io import BytesIO
from controllers.auth_controller import logout_button
from common.ui import sidebar_header
from common.team_profiles import get_team_profile_map, compute_team_profile_outputs, plot_team_profiles_pca

# --- Header layout knobs (easy to tweak) ---
HEADER_POS = {
    "title_y":    0.972,
    "subtitle_y": 0.952,
    "score_y":    0.932,
    "profile_y":  0.917,
    "legend_y":   0.899,
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


def _ensure_auth():
    if not st.session_state.get("authenticated"):
        try:
            st.switch_page("main.py")
        except Exception:
            st.info("Please sign in on **Home** first.")
            st.stop()


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
    """Place a flag image at (left, top) in figure coordinates.

    Implementation notes:
      - This helper is intentionally forgiving: failure to download or open
        the image is caught and silently ignored so that missing flags do not
        break the infographic generation.
      - A desktop User-Agent header is used because some image servers
        block default Python UA strings.
      - The image is placed using `fig.add_axes` with absolute figure
        coordinates so flags remain in consistent positions regardless of
        subplot layouts.
    """
    if not url:
        return

    try:
        from PIL import Image
        import requests
        from io import BytesIO as _BIO

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

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
    fig = plt.figure(figsize=(12.5, 19.5))
    fig.subplots_adjust(top=0.86, bottom=0.08)
    gs = GridSpec(3, 2, figure=fig, height_ratios=[1, 1, 1.15], hspace=0.20, wspace=0.25)

    # Panel 1
    ax1 = fig.add_subplot(gs[0, 0])
    plot_momentum(
        minute_df,
        (home, away),
        goals_df,
        halftime_minute=HALFTIME_MINUTE,
        colors_map={home: col_home, away: col_away},
        ax=ax1,
        show_legend=False,
    )
    ax1.set_title("Attacking momentum by minute", fontsize=8, pad=6, loc="left")

    # Panel 2
    ax2 = fig.add_subplot(gs[0, 1])
    plot_smoothed(
        minute_df,
        (home, away),
        tau_minutes=SMOOTH_TAU_MIN,
        colors_map={home: col_home, away: col_away},
        ax=ax2,
        legend_mode="none",
    )
    ax2.set_title("Smoothed attacking momentum", fontsize=8, pad=6, loc="left")

    # Panel 3
    ax3 = fig.add_subplot(gs[1, 0])
    plot_top_players(
        df_attack,
        top_n=TOP_N_PLAYERS,
        colors_map={home: col_home, away: col_away},
        ax=ax3,
        show_legend=False,
    )
    ax3.set_title(f"Top {TOP_N_PLAYERS} attacking players", fontsize=8, pad=6, loc="left")

    # Panel 4
    ax4 = fig.add_subplot(gs[1, 1])
    plot_cumulative(
        df_attack,
        colors_map={home: col_home, away: col_away},
        ax=ax4,
        show_legend=False,
    )
    ax4.set_title("Cumulative attacking actions", fontsize=8, pad=6, loc="left")

    # Panel 5: PCA team profile chart across the full bottom row
    ax5 = fig.add_subplot(gs[2, :])

    df_profiles, _, _ = compute_team_profile_outputs()
    if not df_profiles.empty:
        plot_team_profiles_pca(
            df_profiles,
            selected_teams=[home, away],
            ax=ax5,
            title="Team tactical clusters (PCA)",
        )

    # Header block
    title = "FIFA Futsal World Cup — Match Infographic"
    parts = [str(match_row["StageName"]).strip()]

    if match_row["StageName"] == "Group Matches":
        group = str(match_row.get("GroupName", "")).strip()
        if group:
            parts.append(group)

    date_val = match_row.get("LocalDate", match_row.get("KickoffDate", ""))
    if date_val:
        parts.append(str(date_val).strip())

    subtitle = " • ".join(parts)
    scoreln = f"{home} {home_g} - {away_g} {away}"

    fig.text(
        0.5,
        HEADER_POS["title_y"],
        title,
        ha="center",
        va="center",
        fontsize=16,
        fontweight="bold",
    )

    fig.text(
        0.5,
        HEADER_POS["subtitle_y"],
        subtitle,
        ha="center",
        va="center",
        fontsize=10,
        color="dimgray",
    )

    fig.text(
        0.5,
        HEADER_POS["score_y"],
        scoreln,
        ha="center",
        va="center",
        fontsize=12,
        fontweight="semibold",
    )

    cluster_map = dict(zip(df_profiles["TeamName"], df_profiles["ClusterLabel"])) if not df_profiles.empty else {}
    home_profile = cluster_map.get(home, "Unknown")
    away_profile = cluster_map.get(away, "Unknown")

    fig.text(
        0.5,
        HEADER_POS["profile_y"],
        f"{home_profile} - {away_profile}",
        ha="center",
        va="center",
        fontsize=9,
    )

    # Compact legend below the score
    handles = [
        Patch(facecolor=col_home, label=home),
        Patch(facecolor=col_away, label=away),
    ]
    fig.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, HEADER_POS["legend_y"]),
        ncol=2,
        frameon=False,
        prop={"size": 10},
    )

    # Flags in the extreme top corners
    _add_flag(fig, flag_left_url, left=0.02, top=0.975, width=0.095)
    _add_flag(fig, flag_right_url, left=0.885, top=0.975, width=0.095)

    # Footer note for academic framing
    fig.text(
        0.5,
        0.02,
        "Source: FIFA Futsal World Cup event data. PCA is used only for visualization of team tactical profiles.",
        ha="center",
        va="center",
        fontsize=7,
        color="dimgray",
    )

    return fig


def main():
    _ensure_auth()
    sidebar_header(user=st.session_state.get("username"), show_custom_nav=True)
    logout_button()

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
                return (
                    get_flag_url_by_team_id(str(match_row["HomeId"])),
                    get_flag_url_by_team_id(str(match_row["AwayId"])),
                )
            except Exception:
                return "", ""

    import pandas as pd

    match_row = pd.Series(st.session_state["match_row"])
    events, squads, _ = load_match_datasets(match_row)
    df_attack = build_attack_df(events, match_row, squads=squads)
    minute_df = build_minute_matrix(df_attack, match_row)
    goals_df = build_goals_only(df_attack)

    pal = pick_match_colors(
        home_name=str(match_row["HomeName"]),
        away_name=str(match_row["AwayName"]),
        home_id=str(match_row["HomeId"]),
        away_id=str(match_row["AwayId"]),
    )
    colors_map = {
        str(match_row["HomeName"]): pal.home_color,
        str(match_row["AwayName"]): pal.away_color,
    }

    home_flag, away_flag = _get_flags(match_row)

    st.header("Infographic")
    st.caption(
        "Static summary figure designed for academic presentation and PDF export."
    )

    fig = _make_figure(
        match_row,
        events,
        df_attack,
        minute_df,
        goals_df,
        colors_map,
        home_flag,
        away_flag,
    )
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