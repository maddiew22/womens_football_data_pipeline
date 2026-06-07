import re
from datetime import datetime

import streamlit as st
import requests
import pandas as pd

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
            list(player_map.keys())
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
            st.subheader("Player Stats")
            st.write(player_stats)

            st.subheader("Seasonal Stats")
            season = st.selectbox(
                "Season",
                sorted(player_stats["season"].unique())
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
            #st.caption(f"Matches Played: {seasonal_stats[""]} • Minutes Played: {country}")

            left, right = st.columns(2)
            with left:
                with st.container(border=True):
                    st.subheader("Defence")
                    st.dataframe(seasonal_stats[STATS_GROUPS["Defence"]], hide_index=True)
                with st.container(border=True):
                    st.subheader("Passing")
                    st.dataframe(seasonal_stats[STATS_GROUPS["Passing"]], hide_index=True)

            with right:
                with st.container(border=True):
                    st.subheader("Offence")
                    st.dataframe(seasonal_stats[STATS_GROUPS["Offence"]], hide_index=True)
                with st.container(border=True):
                    st.subheader("Discipline")
                    st.dataframe(seasonal_stats[STATS_GROUPS["Discipline"]], hide_index=True)

    with tab3:
        st.header("Compare to other players")
        selected_names = st.multiselect(
            "Compare to",
            list(player_map.keys())
        )
        selected_ids = [player_map[name] for name in selected_names]
        all_stats = {}

        for player_id, name in zip(selected_ids, selected_names):
            df = get_player_stats(player_id)
            if df is not None:
                all_stats[name] = df

        for name, df in all_stats.items():
            st.subheader(name)
            st.dataframe(df)

        left, right = st.columns(2)
        with left:
            with st.container(border=True):
                st.subheader("Defence")
            with st.container(border=True):
                st.subheader("Passing")

        with right:
            with st.container(border=True):
                st.subheader("Offence")
            with st.container(border=True):
                st.subheader("Discipline")

with pg2:
    st.header("Leaderboards")

    