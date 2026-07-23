import re
from datetime import datetime
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import requests
import pandas as pd
import sys
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import ast
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scrapers.statsbomb import plot_pass_map, plot_heat_map
from frontend_logic import normalize_comp, parse_competitions_for_leaderboard, get_players, get_player_overview_data, get_player_stats, get_leaderboards, get_competitions, get_available_stats, get_statsbomb_competitions, get_statsbomb_matches, get_statsbomb_passes, get_statsbomb_touches, format_birthdate, parse_secondary_positions, clean_display, build_radar, plot_goal_map, plot_radar, plot_comparison_radar, get_seasons, get_player_shot_stats, get_player_shot_stats_overview, plot_shot_map

STATS_GROUPS = {
    "Defence": ["tackles", "tackles_per90", "defensive_actions", "defensive_actions_per90", "duels_won", "duels_won_per90", "dribbled_past", "dribbled_past_per90", "interceptions", "interceptions_per90", "recoveries", "recoveries_per90", "clearances", "clearances_per90", "possession_won_final_3rd", "possession_won_final_3rd_per90", "aerials_won", "aerials_won_per90", "clean_sheets", "goals_conceded_while_on_pitch", "goals_conceded_while_on_pitch_per90"],
    "Offence": ["goals", "goals_per90", "assists", "assists_per90", "big_chances_created", "big_chances_created_per90", "chances_created", "chances_created_per90", "shots", "shots_per90", "shots_on_target", "shots_on_target_per90", "dribbles", "dribbles_per90", "dribbles_success_rate", "touches_in_opposition_box", "touches_in_opposition_box_per90"],
    "Passing": ["accurate_passes", "accurate_passes_per90", "pass_accuracy", 
                "accurate_long_balls", "accurate_long_balls_per90", "long_ball_accuracy", "successful_crosses", "successful_crosses_per90", "cross_accuracy"],
    "Discipline": ["fouls_committed", "fouls_committed_per90", "yellow_cards", "yellow_cards_per90", "red_cards", 
                   "red_cards_per90", "penalties_conceded", "penalties_conceded_per90"]
}

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
        default_name = "Leah Williamson"
        sorted_names = sorted(player_map.keys())
        default_index = sorted_names.index(default_name) if default_name in sorted_names else 0
        selected_name = st.selectbox(
            "Select Player",
            sorted_names,
            default_index
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

                position = player.get("primary_position")
                foot = player.get("preferred_foot")
                c1.metric(
                    "Primary Position",
                    ("Unknown" if position is None else position).capitalize()
                )

                c2.metric(
                    "Preferred Foot",
                    ("Unknown" if foot is None else foot).capitalize()
                )
                st.divider()

                left, right = st.columns(2)

                with left:
                    with st.container(border=True):
                        st.subheader("Personal")

                        st.write("**Birth Date**")
                        st.write(format_birthdate(player.get("birthdate")))

                        st.write("**Country**")
                        country = player.get("country")
                        st.write(("Unknown" if country is None else country).capitalize())

                        st.write("**Preferred Foot**")
                        foot = player.get("preferred_foot")
                        st.write(("Unknown" if foot is None else foot).capitalize())

                with right:
                    with st.container(border=True):
                        st.subheader("Football")

                        st.write("**Club**")
                        club = player.get("club")
                        st.write(("Unknown" if club is None else club).capitalize())

                        st.write("**Primary Position**")
                        position = player.get("primary_position")
                        st.write(("Unknown" if position is None else position).capitalize())

                        secondary = player.get("secondary_positions")
                        secondary_list = parse_secondary_positions(secondary)
                        secondary_display = "None" if not secondary_list else ", ".join(secondary_list)

                        st.write("**Secondary Positions**")
                        st.write(secondary_display)

        with tab2:
            st.header("Stats")
            player_stats = get_player_stats(selected_id)
            if player_stats is not None:
                try:
                    player_stats = player_stats.sort_values("season", ascending=False)
                    st.subheader("Player Stats")

                    display_df = (
                        player_stats
                        .replace({None: np.nan, "None": np.nan})
                        .drop(
                            columns=[
                                col for col in player_stats.columns
                                if col.endswith("percentile")
                                or col.endswith("percentile_per90")
                            ] + ["player_id", "data_source", "last_updated"],
                            errors="ignore"
                        ).dropna(axis=1, how="all")
                    )
                    # Order cols for display
                    first_cols = [
                        "season",
                        "competition",
                        "matches_played",
                        "minutes_played",
                    ]
                    existing_first_cols = [c for c in first_cols if c in display_df.columns]
                    remaining_cols = [c for c in display_df.columns if c not in existing_first_cols]
                    display_df = display_df[existing_first_cols + remaining_cols]

                    st.dataframe(display_df, hide_index=True)
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
                    with st.container(border=True):
                        st.subheader("Shot Overview")
                        shots_df = get_player_shot_stats(selected_id, season, competition)
                        shot_overview_stats = get_player_shot_stats_overview(selected_id, season, competition)
                        
                        exclude_cols = ["player_id", "season", "competition"]
                        # st.dataframe(
                        #     shot_overview_stats.drop(columns=exclude_cols, errors="ignore"),
                        #     hide_index=True,
                        # )
                   
                        try:
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("Shot Map")
                                st.pyplot(plot_shot_map(shots_df), use_container_width=True)
                            with col2:
                                st.markdown("Goal Map")
                                st.pyplot(plot_goal_map(shots_df), use_container_width=True)
                            st.divider()
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.markdown("Conversion Rate")

                                conversion_rate = shot_overview_stats["conversion_rate"].iloc[0]
                                fig = go.Figure()
                                fig.add_bar(
                                    x=[100],
                                    y=[""],
                                    orientation="h",
                                    marker_color="#3a3a3a",
                                    width=1.5,
                                    hoverinfo="skip",
                                )
                                # Filled accuracy bar
                                fig.add_bar(
                                    x=[conversion_rate],
                                    y=[""],
                                    orientation="h",
                                    marker_color="#2e70cc",
                                    width=1.5,
                                    hoverinfo="skip",
                                )
                                # Percentage label in center of bar
                                fig.add_annotation(
                                    x=conversion_rate / 2,
                                    y=0,
                                    text=f"<b>{conversion_rate:.1f}%</b>",
                                    showarrow=False,
                                    font=dict(
                                        color="white",
                                        size=14
                                    ),
                                )
                                fig.update_layout(
                                    barmode="overlay",
                                    height=50,
                                    margin=dict(l=20, r=20, t=10, b=10),
                                    xaxis=dict(
                                        range=[0, 100],
                                        visible=False,
                                        fixedrange=True,
                                    ),
                                    yaxis=dict(
                                        visible=False,
                                        range=[-1, 1],
                                        fixedrange=True,
                                    ),
                                    paper_bgcolor="#1e1e1e",
                                    plot_bgcolor="#1e1e1e",
                                    showlegend=False,
                                )
                                fig.update_traces(
                                    marker_line_width=0
                                )
                                st.plotly_chart(fig, use_container_width=True)
                                # st.progress(shot_overview_stats["conversion_rate"].iloc[0]/100)
                                # st.caption(f"{shot_overview_stats['conversion_rate'].iloc[0]:.1f}%")

                                body = pd.DataFrame({
                                    "Body Part": [
                                        "Right Foot",
                                        "Left Foot",
                                        "Header",
                                        "Other"
                                    ],
                                    "Shots": [
                                        shot_overview_stats["right_foot_shots"].iloc[0],
                                        shot_overview_stats["left_foot_shots"].iloc[0],
                                        shot_overview_stats["header_shots"].iloc[0],
                                        shot_overview_stats["other_body_part_shots"].iloc[0]
                                    ]
                                })
                                fig = px.pie(
                                    body,
                                    names="Body Part",
                                    values="Shots",
                                    hole=0.6,
                                    title="Shot Body Part Distribution"
                                )
                                fig.update_traces(textposition="inside", textinfo="percent+label")
                                st.plotly_chart(fig, use_container_width=True)

                                situations = pd.DataFrame({
                                    "Situation": [
                                        "Regular Play",
                                        "Corner",
                                        "Set Piece",
                                        "Other"
                                    ],
                                    "Shots": [
                                        shot_overview_stats["regular_play_shots"].iloc[0],
                                        shot_overview_stats["corner_shots"].iloc[0],
                                        shot_overview_stats["set_piece_shots"].iloc[0],
                                        shot_overview_stats["other_situation_shots"].iloc[0]
                                    ]
                                })
                                fig = px.bar(
                                    situations,
                                    x="Shots",
                                    y="Situation",
                                    orientation="h",
                                    text="Shots",
                                    title="Shot Situation Distribution"
                                )
                                st.plotly_chart(fig, use_container_width=True)


                                goal_context = pd.DataFrame({
                                    "Situation": [
                                        "Go Ahead",
                                        "Leveller",
                                        "Insurance",
                                        "Consolation"
                                    ],
                                    "Goals": [
                                        shot_overview_stats["go_ahead_goals"].iloc[0],
                                        shot_overview_stats["leveller_goals"].iloc[0],
                                        shot_overview_stats["insurance_goals"].iloc[0],
                                        shot_overview_stats["consolation_goals"].iloc[0]
                                    ]
                                })
                                # remove zero categories
                                goal_context = goal_context[goal_context["Goals"] > 0]
                                fig = px.pie(
                                    goal_context,
                                    names="Situation",
                                    values="Goals",
                                    hole=0.55,
                                    title="Goals by Game Situation"
                                )
                                fig.update_traces(
                                    textposition="inside",
                                    textinfo="label+value"
                                )

                                st.plotly_chart(fig, use_container_width=True)

                            with col_b:
                                st.markdown("Shot Accuracy")
                            
                                accuracy = shot_overview_stats["shot_accuracy"].iloc[0]
                                fig = go.Figure()
                                fig.add_bar(
                                    x=[100],
                                    y=[""],
                                    orientation="h",
                                    marker_color="#3a3a3a",
                                    width=1.5,
                                    hoverinfo="skip",
                                )
                                # Filled accuracy bar
                                fig.add_bar(
                                    x=[accuracy],
                                    y=[""],
                                    orientation="h",
                                    marker_color="#2e70cc",
                                    width=1.5,
                                    hoverinfo="skip",
                                )
                                # Percentage label in center of bar
                                fig.add_annotation(
                                    x=accuracy / 2,
                                    y=0,
                                    text=f"<b>{accuracy:.1f}%</b>",
                                    showarrow=False,
                                    font=dict(
                                        color="white",
                                        size=14
                                    ),
                                )
                                fig.update_layout(
                                    barmode="overlay",
                                    height=50,
                                    margin=dict(l=20, r=20, t=10, b=10),
                                    xaxis=dict(
                                        range=[0, 100],
                                        visible=False,
                                        fixedrange=True,
                                    ),
                                    yaxis=dict(
                                        visible=False,
                                        range=[-1, 1],
                                        fixedrange=True,
                                    ),
                                    paper_bgcolor="#1e1e1e",
                                    plot_bgcolor="#1e1e1e",
                                    showlegend=False,
                                )
                                fig.update_traces(
                                    marker_line_width=0
                                )
                                st.plotly_chart(fig, use_container_width=True)
                                # st.progress(shot_overview_stats["shot_accuracy"].iloc[0]/100)
                                # st.caption(f"{shot_overview_stats['shot_accuracy'].iloc[0]:.1f}%")

                                location = pd.DataFrame({
                                    "Location": [
                                        "Inside Box",
                                        "Outside Box"
                                    ],
                                    "Shots": [
                                        shot_overview_stats["inside_box_shots"].iloc[0],
                                        shot_overview_stats["outside_box_shots"].iloc[0]
                                    ]
                                })
                                fig = px.pie(
                                    location,
                                    names="Location",
                                    values="Shots",
                                    hole=0.6,
                                    title="Shot Location Distribution"
                                )
                                st.plotly_chart(fig, use_container_width=True)


                                bins = [-np.inf, 0.1, 0.2, 0.4, np.inf]
                                labels = [
                                    "Poor (<0.1)",
                                    "Average (0.1-0.2)",
                                    "Good (0.2-0.4)",
                                    "Great (>0.4)"
                                ]
                                shots_df["shot_quality"] = pd.cut(
                                    shots_df["expected_goals"],
                                    bins=bins,
                                    labels=labels
                                )
                                # Count all shots
                                all_shots = (
                                    shots_df["shot_quality"]
                                    .value_counts()
                                    .reindex(labels)
                                    .fillna(0)
                                )
                                # Count converted shots
                                converted_shots = (
                                    shots_df[shots_df["event_type"] == "Goal"]["shot_quality"]
                                    .value_counts()
                                    .reindex(labels)
                                    .fillna(0)
                                )
                                shot_quality_df = pd.DataFrame({
                                    "Shot Quality": labels,
                                    "All Shots": all_shots.values,
                                    "Goals": converted_shots.values
                                })

                                # Convert to long format
                                plot_df = shot_quality_df.melt(
                                    id_vars="Shot Quality",
                                    value_vars=["All Shots", "Goals"],
                                    var_name="Type",
                                    value_name="Count"
                                )

                                # Plot
                                fig = px.bar(
                                    plot_df,
                                    x="Shot Quality",
                                    y="Count",
                                    color="Type",
                                    barmode="group",
                                    text="Count",
                                    title="Shot Quality Distribution"
                                )

                                fig.update_traces(
                                    textposition="outside"
                                )

                                fig.update_layout(
                                    template="plotly_white",
                                    xaxis_title="Chance Quality (xG)",
                                    yaxis_title="Number of Shots",
                                    legend_title=""
                                )

                                st.plotly_chart(
                                    fig,
                                    use_container_width=True
                                )
                            
                        except Exception as e:
                            print(e)
                            st.info("Not enough data for shot map or goal map")

                    st.subheader("Passing and Heat Maps")

                    player_stats = get_player_stats(selected_id)

                    if player_stats is not None and not player_stats.empty:

    
                            comp_options = get_statsbomb_competitions(selected_name)
                            selected_comp = st.selectbox(
                                "Competition",
                                comp_options,
                                #key="map_competition"
                            )

                            try:

                                player_matches = get_statsbomb_matches(
                                    selected_name,
                                    selected_comp
                                )

                                if player_matches.empty:

                                    st.warning(
                                        "No passing/heat map data available for this player."
                                    )

                                else:

                                    match_labels = player_matches["match_date"].tolist()
            
                                    selected_idx = st.selectbox(
                                        "Match",
                                        options=player_matches.index,
                                        format_func=lambda i: (
                                            f"{player_matches.loc[i, 'match_date']} - "
                                            f"{player_matches.loc[i, 'team_name']}"
                                        )
                                    )

                                    selected_match = player_matches.loc[selected_idx]
                                    st.divider()

                                    st.subheader("Pass Map")
                                    passes_df = get_statsbomb_passes(selected_match["display_name"], selected_match["match_id"])
                                    touches_df = get_statsbomb_touches(selected_match["display_name"], selected_match["match_id"])
                                    fig, passes_completed, passes_failed, passes_received = (
                                        plot_pass_map(selected_match["display_name"], passes_df)
                                    )

                                    st.pyplot(fig)

                                    st.caption(
                                        f"Completed passes: {passes_completed} | "
                                        f"Failed: {passes_failed}"
                                    )

                                    st.divider()

                                    st.subheader("Heat Map")

                                    fig, total_actions, def_half, off_half = (
                                        plot_heat_map(selected_match["display_name"], touches_df)
                                    )

                                    st.pyplot(fig)

                                    st.caption(
                                        f"Total actions: {total_actions} | "
                                        f"Defensive Half Utilization: {def_half:.1f}% | "
                                        f"Offensive Half Utilization: {off_half:.1f}%"
                                    )

                            except Exception as e:
                                print(e)
                                st.info("Not enough data")

                except Exception as e:
                    print(e)
                    st.info("Not enough data for player")
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

    stats = get_available_stats()
    all_stats = stats["column_name"].tolist()
    all_stats = [s for s in all_stats if "percentile" not in s.lower()]

    default_stat = "assists"
    default_index = all_stats.index(default_stat) if default_stat in all_stats else 0

    selected_stat = st.selectbox(
        "Select Stat",
        options=all_stats,
        index=default_index
    )

    selected_position = st.selectbox(
        "Filter Position",
        options=[
            "All",
            "Center Back",
            "Full Back",
            "Central Midfielder",
            "Winger",
            "Striker",
        ],
    )

    position_mapping = {
        "Center Back": ["Center Back", "Defender"],
        "Full Back": ["Left Back", "Right Back", "Full Back", "Defender"],
        "Central Midfielder": [
            "Midfielder",
            "Central Midfielder",
            "Defensive Midfielder",
            "Attacking Midfielder",
        ],
        "Winger": ["Left Winger", "Right Winger", "Winger"],
        "Striker": ["Striker", "Centre Forward", "Forward"],
    }

    season_options = get_seasons()
    season_options = sorted(season_options["season"], reverse=True)

    selected_season = st.selectbox(
        "Season",
        options=season_options,
    )

    comps_to_exclude = [
        "WSL 2",
        "NWSL Challenge Cup",
        "A-League Women",
        "NWSL Fall Series Northeast",
        "NWSL Fall Series West",
        "NWSL Fall Series South",
        "Concacaf W Qualifiers",
        "W-League",
        "Summer Olympics Women",
    ]

    comps = get_competitions(season)
    all_comps = [
        c for c in comps["competition"].tolist()
        if c not in comps_to_exclude
    ]

    selected_comps = st.multiselect(
        "Filter Competitions",
        options=all_comps
    )
    min_mins_filter = st.slider(
       "Minimum Minutes Played",
        min_value=0,
        max_value=2000,
        value=500
    )

    df = get_leaderboards(
        season=selected_season,
        stat=selected_stat,
    )

    if selected_comps:
        df = df[df["competition"].isin(selected_comps)]

    if selected_position != "All":
        df = df[df["primary_position"].isin(position_mapping[selected_position])]

    df[f"{selected_stat}"] = pd.to_numeric(df[f"{selected_stat}"], errors="coerce")
    stat_lower = selected_stat.lower()

    avg_keywords = ["rate", "percentage", "per90", "accuracy"]

    agg_func = (
        "mean"
        if any(keyword in stat_lower for keyword in avg_keywords)
        else "sum"
    )

    leaderboard = (
        df.groupby(
            ["player_name", "primary_position"],
            as_index=False,
        )
        .agg(
            value=(selected_stat, agg_func),
            minutes_played=("minutes_played", "sum"),
            competitions=("competition", lambda x: ", ".join(sorted(set(x))))
        )
    )
    leaderboard = leaderboard[
        pd.to_numeric(leaderboard["minutes_played"]) >= min_mins_filter
    ]

    st.dataframe(
        leaderboard[
            ["player_name", "value", "primary_position", "competitions", "minutes_played"]
        ]
        .sort_values("value", ascending=False)
        .head(20),
        use_container_width=True,
        hide_index=True,
    )