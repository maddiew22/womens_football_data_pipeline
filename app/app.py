import re
from datetime import datetime
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import requests
import pandas as pd
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force reload of scrapers modules to pick up latest changes
if 'scrapers' in sys.modules:
    del sys.modules['scrapers']
if 'scrapers.statsbomb' in sys.modules:
    del sys.modules['scrapers.statsbomb']

from scrapers.statsbomb import plot_pass_map, get_womens_base_competitions, plot_heat_map, get_player_matches

BASE_URL = "http://127.0.0.1:8000"

STATS_GROUPS = {
    "Defence": ["tackles", "tackles_per90", "defensive_actions", "defensive_actions_per90", "duels_won", "duels_won_per90", "dribbled_past", "dribbled_past_per90", "interceptions", "interceptions_per90", "recoveries", "recoveries_per90", "clearances", "clearances_per90", "possession_won_final_3rd", "possession_won_final_3rd_per90", "aerials_won", "aerials_won_per90", "clean_sheets", "goals_conceded_while_on_pitch", "goals_conceded_while_on_pitch_per90"],
    "Offence": ["goals", "goals_per90", "assists", "assists_per90", "big_chances_created", "big_chances_created_per90", "chances_created", "chances_created_per90", "shots", "shots_per90", "shots_on_target", "shots_on_target_per90", "dribbles", "dribbles_per90", "dribbles_success_rate", "touches_in_opposition_box", "touches_in_opposition_box_per90"],
    "Passing": ["accurate_passes", "accurate_passes_per90", "pass_accuracy", 
                "accurate_long_balls", "accurate_long_balls_per90", "long_ball_accuracy", "successful_crosses", "successful_crosses_per90", "cross_accuracy"],
    "Discipline": ["fouls_committed", "fouls_committed_per90", "yellow_cards", "yellow_cards_per90", "red_cards", 
                   "red_cards_per90", "penalties_conceded", "penalties_conceded_per90"]
}

def get_players():
    try:
        response = requests.get(f"{BASE_URL}/players")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to load players: {e}")
        return []


def get_player_overview_data(player_id):
    try:
        response = requests.get(f"{BASE_URL}/players/bio/{player_id}")
        response.raise_for_status()
        json_data = response.json()
        return pd.DataFrame(json_data)
    except Exception as e:
        st.error(f"Failed to load player data: {e}")
        return None

def get_player_stats(player_id):
    try:
        response = requests.get(f"{BASE_URL}/players/stats/{player_id}")
        response.raise_for_status()
        json_data = response.json()    
        return pd.DataFrame(json_data)
    except Exception as e:
        st.error(f"Failed to load player stats: {e}")
        return None


def format_birthdate(value):
    if not value:
        return "Unknown"

    try:
        value_str = str(value).strip()
        if value_str.endswith("Z"):
            value_str = value_str[:-1]
        dt = datetime.fromisoformat(value_str)
        return dt.strftime("%b %d, %Y")
    except Exception:
        return str(value)


def parse_secondary_positions(raw):
    if not raw:
        return []

    raw_str = str(raw).strip()
    if raw_str.startswith("[") and raw_str.endswith("]"):
        matches = re.findall(r"['\"]([^'\"]+)['\"]", raw_str)
        if matches:
            return [m.strip() for m in matches if m.strip()]

        inner = raw_str[1:-1].strip()
        if "," in inner:
            return [item.strip() for item in inner.split(",") if item.strip()]
        return [item.strip() for item in re.split(r'(?<=[a-z])(?=[A-Z])', inner) if item.strip()]

    if raw_str.startswith("'") and raw_str.endswith("'"):
        raw_str = raw_str[1:-1].strip()
    elif raw_str.startswith('"') and raw_str.endswith('"'):
        raw_str = raw_str[1:-1].strip()

    if "," in raw_str:
        return [item.strip() for item in raw_str.split(",") if item.strip()]
    if re.search(r'(?<=[a-z])(?=[A-Z])', raw_str):
        return [item.strip() for item in re.split(r'(?<=[a-z])(?=[A-Z])', raw_str) if item.strip()]

    return [raw_str]

def clean_display(df, cols):
    cols = [c for c in cols if c in df.columns]
    cleaned = df[cols].dropna(axis=1)
    return cleaned

def build_radar(df, cols, suffix="percentile"):
    base_cols = [
        c for c in cols
        if c in df.columns and not c.endswith("_per90")
    ]

    pct_pairs = [
        (c, f"{c}_{suffix}")
        for c in base_cols
        if f"{c}_{suffix}" in df.columns
    ]

    labels = []
    values = []

    for base, pct in pct_pairs:
        val = df[pct].iloc[0]

        if pd.isna(val):
            continue

        labels.append(base.replace("_", " ").title())
        values.append(val)

    if len(values) < 3:
        return [], []

    labels += [labels[0]]
    values += [values[0]]

    return labels, values

def plot_radar(labels, values, title="Radar"):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=labels,
        fill='toself',
        name=title
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100])
        ),
        showlegend=False,
        title=title
    )
    st.plotly_chart(fig, use_container_width=True)

def get_common_radar_axes(player_data, cols, suffix):
    base_cols = [
        c for c in cols
        if not c.endswith("_per90")
    ]
    common = []
    for col in base_cols:
        pct_col = f"{col}_{suffix}"
        if all(
            pct_col in df.columns and pd.notna(df[pct_col].iloc[0])
            for df in player_data.values()
        ):
            common.append(col)
    return common

def plot_comparison_radar(player_data, cols, title, suffix):

    common_axes = get_common_radar_axes(player_data, cols, suffix)
    if len(common_axes) < 3:
        st.warning(f"Not enough shared data for {title}")
        return
    labels = [c.replace("_", " ").title() for c in common_axes]
    fig = go.Figure()
    for player_name, df in player_data.items():
        values = [df[f"{col}_{suffix}"].iloc[0] for col in common_axes]
        fig.add_trace(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=labels + [labels[0]],
                fill="toself",
                name=player_name,
                opacity=0.35
            )
        )
    fig.update_layout(
        title=title,
        polar=dict(radialaxis=dict(visible=True,range=[0, 100])),
        showlegend=True
    )
    st.plotly_chart(fig, use_container_width=True)

# Page Config
st.set_page_config(
    page_title="Women's Football Data App",
    layout="wide"
)
# UI
st.title("Women's Football Data App")
pg1, pg2 = st.tabs(["Player", "Leaderboards"])
# Load players
players = get_players()
if not players:
    st.warning("No players loaded. Is the backend running?")
    st.stop()
player_map = {p["player_name"]: p["player_id"] for p in players}

with pg1:
    with st.container(border=True):
        selected_name = st.selectbox(
            "Select Player",
            sorted(player_map.keys())
        )

        selected_id = player_map[selected_name]

        tab1, tab2, tab3 = st.tabs(["Overview", "Stats", "Compare"])
        with tab1:
            st.header(selected_name)
            player_overview = get_player_overview_data(selected_id)
            if player_overview is not None:
                player = player_overview.iloc[0]
                club = player.get("club", "Unknown Club")
                country = player.get("country", "Unknown Country")
                st.caption(f"{club} • {country}")
                c1, c2 = st.columns(2)

                c1.metric(
                    "Primary Position",
                    player.get("primary_position", "Unknown").capitalize()
                )

                c2.metric(
                    "Preferred Foot",
                    player.get("preferred_foot", "Unknown").capitalize()
                )
                st.divider()

                left, right = st.columns(2)

                with left:
                    with st.container(border=True):
                        st.subheader("Personal")

                        st.write("**Birth Date**")
                        st.write(format_birthdate(player.get("birthdate")))

                        st.write("**Country**")
                        st.write(player.get("country", "Unknown").capitalize())

                        st.write("**Preferred Foot**")
                        st.write(player.get("preferred_foot", "Unknown").capitalize())

                with right:
                    with st.container(border=True):
                        st.subheader("Football")

                        st.write("**Club**")
                        st.write(player.get("club", "Unknown").capitalize())

                        st.write("**Primary Position**")
                        st.write(player.get("primary_position", "Unknown").capitalize())

                        secondary = player.get("secondary_positions")
                        secondary_list = parse_secondary_positions(secondary)
                        secondary_display = "None" if not secondary_list else ", ".join(secondary_list)

                        st.write("**Secondary Positions**")
                        st.write(secondary_display)

        with tab2:
            st.header("Stats")
            player_stats = get_player_stats(selected_id)
            if player_stats is not None:
                player_stats = player_stats.sort_values("season", ascending=False)
                st.subheader("Player Stats")

                st.dataframe(
                    player_stats.drop(
                        columns=[
                            col for col in player_stats.columns
                            if col.endswith("percentile")
                            or col.endswith("percentile_per90")
                        ] + ["player_id"],
                        errors="ignore"
                    ),hide_index=True
                )
                st.subheader("Seasonal Stats")
                season = st.selectbox(
                    "Season",
                    sorted(player_stats["season"].unique(), reverse=True)
                )
                # Competition selector filtered by season
                competition = st.selectbox(
                    "Competition",
                    sorted(
                        player_stats.loc[player_stats["season"] == season, "competition"].unique()
                    )
                )
                row = player_stats[
                    (player_stats["season"] == season)
                    & (player_stats["competition"] == competition)
                ].iloc[0]
                seasonal_stats = row.to_frame().T
                seasonal_stats = seasonal_stats.apply(pd.to_numeric, errors="ignore")
                seasonal_stats = seasonal_stats.replace(["None", "nan", "NaN", ""], np.nan)
                #st.caption(f"Matches Played: {seasonal_stats[""]} • Minutes Played: {country}")

                radar_mode = st.radio(
                    "Radar type",
                    ["Regular", "Per90"],
                    horizontal=True
                )
                suffix = "percentile_per90" if radar_mode == "Per90" else "percentile"
                left, right = st.columns(2)
                with left:
                    with st.container(border=True):
                        st.subheader("Defence")

                        labels, values = build_radar(
                            seasonal_stats,
                            STATS_GROUPS["Defence"],
                            suffix=suffix
                        )
                        if values:
                            plot_radar(labels, values, "Defence")
                        st.divider()
                        st.dataframe(
                            clean_display(seasonal_stats, STATS_GROUPS["Defence"]),
                            hide_index=True
                        )

                    with st.container(border=True):
                        st.subheader("Passing")
                        labels, values = build_radar(
                            seasonal_stats,
                            STATS_GROUPS["Passing"],
                            suffix=suffix
                        )
                        if values:
                            plot_radar(labels, values, "Passing")
                        st.divider()
                        st.dataframe(
                            clean_display(seasonal_stats, STATS_GROUPS["Passing"]),
                            hide_index=True
                        )

                with right:
                    with st.container(border=True):
                        st.subheader("Offence")
                        labels, values = build_radar(
                            seasonal_stats,
                            STATS_GROUPS["Offence"],
                            suffix=suffix
                        )
                        if values:
                            plot_radar(labels, values, "Offence")

                        st.divider()

                        st.dataframe(
                            clean_display(seasonal_stats, STATS_GROUPS["Offence"]),
                            hide_index=True
                        )

                    with st.container(border=True):
                        st.subheader("Discipline")
                        labels, values = build_radar(
                            seasonal_stats,
                            STATS_GROUPS["Discipline"],
                            suffix=suffix
                        )
                        if values:
                            plot_radar(labels, values, "Discipline")
                        st.divider()
                        st.dataframe(
                            clean_display(seasonal_stats, STATS_GROUPS["Discipline"]),
                            hide_index=True
                        )

                st.subheader("Passing and Heat Maps")

                player_stats = get_player_stats(selected_id)

                if player_stats is not None and not player_stats.empty:

                    player_competitions = sorted(
                        player_stats["competition"].unique()
                    )

                    player_bases = [
                        c.split("(")[0].strip()
                        for c in player_competitions
                    ]

                    sb_bases = get_womens_base_competitions()

                    player_bases_lower = [
                        b.lower()
                        for b in player_bases
                    ]

                    sb_bases_lower = [
                        b.lower()
                        for b in sb_bases
                    ]

                    common_lower = (
                        set(player_bases_lower)
                        & set(sb_bases_lower)
                    )

                    common = [
                        b
                        for b in sb_bases
                        if b.lower() in common_lower
                    ]

                    if not common:
                        st.warning(
                            "No available map data"
                        )

                    else:

                        selected_comp = st.selectbox(
                            "Competition",
                            common,
                            key="map_competition"
                        )

                        try:

                            player_matches = get_player_matches(
                                selected_name,
                                selected_comp
                            )

                            if not player_matches:

                                st.warning(
                                    "No matches found for this player."
                                )

                            else:

                                match_labels = [
                                    m["label"]
                                    for m in player_matches
                                ]

                                selected_match_label = st.selectbox(
                                    "Match",
                                    match_labels,
                                    key="map_match"
                                )

                                selected_match = next(
                                    m
                                    for m in player_matches
                                    if m["label"]
                                    == selected_match_label
                                )

                                st.divider()

                                st.subheader("Pass Map")

                                fig, passes_completed, passes_failed, passes_received = (
                                    plot_pass_map(
                                        selected_match["player_name"],
                                        selected_match["match_id"]
                                    )
                                )

                                st.pyplot(fig)

                                st.caption(
                                    f"Completed passes: {passes_completed} | "
                                    f"Failed: {passes_failed} | "
                                    f"Received: {passes_received}"
                                )

                                st.divider()

                                st.subheader("Heat Map")

                                fig, total_actions, def_half, off_half = (
                                    plot_heat_map(
                                        selected_match["player_name"],
                                        selected_match["match_id"]
                                    )
                                )

                                st.pyplot(fig)

                                st.caption(
                                    f"Total actions: {total_actions} | "
                                    f"Defensive Half Utilization: {def_half:.1f}% | "
                                    f"Offensive Half Utilization: {off_half:.1f}%"
                                )

                        except Exception as e:

                            st.error(str(e))
        with tab3:
            st.header("Compare Players")
            selected_names = st.multiselect(
                "Players",
                sorted(player_map.keys()),
                default=[selected_name]
            )

            if len(selected_names) < 2:
                st.info("Select at least 2 players to compare.")
            else:

                radar_mode = st.radio(
                    "Radar Type",
                    ["Regular", "Per90"],
                    horizontal=True,
                    key="compare_radar_mode"
                )

                suffix = (
                    "percentile_per90"
                    if radar_mode == "Per90"
                    else "percentile"
                )
                st.subheader("Player Seasons")
                comparison_rows = {}
                for name in selected_names:
                    player_id = player_map[name]
                    df = get_player_stats(player_id)
                    if df is None or df.empty:
                        continue
                    df = df.sort_values("season", ascending=False)
                    with st.expander(name, expanded=True):
                        season = st.selectbox(
                            "Season",
                            sorted(
                                df["season"].unique(),
                                reverse=True
                            ),
                            key=f"season_{player_id}"
                        )
                        competition = st.selectbox(
                            "Competition",
                            sorted(
                                df.loc[
                                    df["season"] == season,
                                    "competition"
                                ].unique()
                            ),
                            key=f"competition_{player_id}"
                        )
                        selected_row = df[
                            (df["season"] == season)
                            & (df["competition"] == competition)
                        ]
                        if selected_row.empty:
                            st.warning(
                                "No data found for this selection."
                            )
                            continue
                        row_df = selected_row.iloc[0].to_frame().T
                        row_df = row_df.apply(
                            pd.to_numeric,
                            errors="ignore"
                        )
                        row_df = row_df.replace(
                            ["None", "nan", "NaN", ""],
                            np.nan
                        )
                        comparison_rows[name] = row_df
                        st.caption(
                            f"Using {season} • {competition}"
                        )
                if comparison_rows:
                    st.divider()
                    left, right = st.columns(2)
                    with left:
                        with st.container(border=True):
                            st.subheader("Defence")
                            plot_comparison_radar(
                                comparison_rows,
                                STATS_GROUPS["Defence"],
                                "Defence Comparison",
                                suffix
                            )
                        with st.container(border=True):
                            st.subheader("Passing")
                            plot_comparison_radar(
                                comparison_rows,
                                STATS_GROUPS["Passing"],
                                "Passing Comparison",
                                suffix
                            )
                    with right:
                        with st.container(border=True):
                            st.subheader("Offence")
                            plot_comparison_radar(
                                comparison_rows,
                                STATS_GROUPS["Offence"],
                                "Offence Comparison",
                                suffix
                            )

                        with st.container(border=True):
                            st.subheader("Discipline")
                            plot_comparison_radar(
                                comparison_rows,
                                STATS_GROUPS["Discipline"],
                                "Discipline Comparison",
                                suffix
                            )
                    st.divider()
                    st.subheader("Selected Data")
                    for name, df in comparison_rows.items():
                        with st.expander(f"{name} Data",expanded=False):
                            st.dataframe(
                                df.drop(
                                    columns=[
                                        c
                                        for c in df.columns
                                        if c.endswith("percentile")
                                        or c.endswith(
                                            "percentile_per90"
                                        )
                                    ],
                                    errors="ignore"
                                ),
                                hide_index=True
                            )
        # with tab4:
        #     st.subheader("Trends")

with pg2:
    st.header("Leaderboards")

    