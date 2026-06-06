import streamlit as st
import requests
import pandas as pd

BASE_URL = "http://127.0.0.1:8000"

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
        return response.json()
    except Exception as e:
        st.error(f"Failed to load player data: {e}")
        return None


# UI
st.title("Women's Football Data App")

# Load players
players = get_players()

if not players:
    st.warning("No players loaded. Is the backend running?")
    st.stop()

player_map = {p["player_name"]: p["player_id"] for p in players}
selected_name = st.selectbox(
    "Select Player",
    list(player_map.keys())
)

selected_id = player_map[selected_name]

# Load selected player's overview
player_overview = get_player_overview_data(selected_id)

if player_overview is not None:
    st.subheader("Player Overview")
    st.write(player_overview)