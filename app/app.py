import streamlit as st
import requests
import pandas as pd

def get_players():
    response = requests.get(f"http://127.0.0.1:8000/players")
    return response.json()

st.title("Women's Football Data App")

# Player Search Bar 
players = get_players()
player_map = {p["player_name"]: p["player_id"] for p in players}
selected_name = st.selectbox(
    "Select Player",
    list(player_map.keys())
)
selected_id = player_map[selected_name]

st.write("Selected ID:", selected_id)