import re
from datetime import datetime
import streamlit as st
import plotly.graph_objects as go
import requests
import pandas as pd
import plotly.express as px
import ast

BASE_URL = "http://127.0.0.1:8000"

COMPETITION_ALIASES = {
    "fa women's super league": "wsl",
    "fa women's super league": "women's super league",
    "wsl": "women's super league",
    "serie a femminile": "serie a women",
    "national women's soccer league": "nwsl",
    "uefa womens champions league": "uwcl",
    "primera division femenina": "liga f",
    "frauen-bundesliga": "frauen bundesliga"
}

def normalize_comp(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"\s*\(\d{4}/\d{4}\)\s*", "", name)  # remove seasons
    return COMPETITION_ALIASES.get(name, name)

def parse_competitions_for_leaderboard(x):
    """Format competitions list for leaderboard"""
    if isinstance(x, list):
        return x

    if not isinstance(x, str):
        return []

    matches = re.finditer(r'"([^"]*)"|\'([^\']*)\'', x)
    return [m.group(1) or m.group(2) for m in matches]

def get_players():
    """Get Players from API"""
    try:
        response = requests.get(f"{BASE_URL}/players", timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to load players: {e}")
        return []


def get_player_overview_data(player_id):
    """Get player overview data from API for a given player"""
    try:
        response = requests.get(f"{BASE_URL}/players/bio/{player_id}", timeout=60)
        response.raise_for_status()
        json_data = response.json()
        return pd.DataFrame(json_data)
    except Exception as e:
        st.error(f"Failed to load player data: {e}")
        return None

def get_player_stats(player_id):
    """Get player stats from API for a given player"""
    try:
        response = requests.get(f"{BASE_URL}/players/stats/{player_id}", timeout=60)
        response.raise_for_status()
        json_data = response.json()    
        return pd.DataFrame(json_data)
    except Exception as e:
        st.error(f"Failed to load player stats: {e}")
        return None

def get_leaderboards(stat, competition=None):
    """Get leaderboard data for a given stat from API"""
    try:
        params = {}
        if competition:
            if isinstance(competition, str):
                competition = [competition]
            params["competition"] = competition 
        response = requests.get(
            f"{BASE_URL}/leaderboards/{stat}",
            params=params,
            timeout=60
        )
        response.raise_for_status()
        json_data = response.json()
        return pd.DataFrame(json_data)

    except Exception as e:
        st.error(f"Failed to load leaderboards: {e}")
        return None

def get_competitions():
    """Get competitions from API"""
    try:
        response = requests.get(f"{BASE_URL}/competitions", timeout=60)
        response.raise_for_status()
        json_data = response.json()    
        return pd.DataFrame(json_data)
    except Exception as e:
        st.error(f"Failed to load competitions: {e}")
        return None 

def get_available_stats():
    """Get season stat names that are available for players from API"""
    try:
        response = requests.get(f"{BASE_URL}/available_stats", timeout=60)
        response.raise_for_status()
        json_data = response.json()    
        return pd.DataFrame(json_data)
    except Exception as e:
        st.error(f"Failed to load stats: {e}")
        return None 
    
def get_statsbomb_competitions(player):
    """Get statsbomb competitions from API"""
    try:
        response = requests.get(f"{BASE_URL}/statsbomb/competitions/{player}", timeout=60)
        response.raise_for_status()
        json_data = response.json()    
        return pd.DataFrame(json_data)
    except Exception as e:
        st.error(f"Failed to load player competitions: {e}")
        return None 

def get_statsbomb_matches(player, competition):
    """Get statsbomb matches from API"""
    try:
        response = requests.get(f"{BASE_URL}/statsbomb_matches/{competition}/{player}", timeout=60)
        response.raise_for_status()
        json_data = response.json()    
        return pd.DataFrame(json_data)
    except Exception as e:
        st.error(f"Failed to load player matches: {e}")
        return None 
    
def get_statsbomb_passes(player, match):
    """Get statsbomb pass events from API"""
    try:
        response = requests.get(f"{BASE_URL}/statsbomb_passes/{match}/{player}", timeout=60)
        response.raise_for_status()
        json_data = response.json()    
        return pd.DataFrame(json_data)
    except Exception as e:
        st.error(f"Failed to load match passes: {e}")
        return None 
    
def get_statsbomb_touches(player, match):
    """Get statsbomb touch events from API"""
    try:
        response = requests.get(f"{BASE_URL}/statsbomb_events/{match}/{player}", timeout=60)
        response.raise_for_status()
        json_data = response.json()    
        return pd.DataFrame(json_data)
    except Exception as e:
        st.error(f"Failed to load match touches: {e}")
        return None 

def format_birthdate(value):
    """Format birthdate in format Mar 29, 1997"""
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
    """Extract secondary positions"""
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
    """Remove columns with na"""
    cols = [c for c in cols if c in df.columns]
    cleaned = df[cols].dropna(axis=1)
    return cleaned

def build_radar(df, cols, suffix="percentile"):
    """Build radar plot of player's stats"""
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
    """Plot radar plot of player's stats"""
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
    """Get common stats non na stats between players for plotting comparison radar"""
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
    """Plot radar of stats to compare 2+ players"""
    common_axes = get_common_radar_axes(player_data, cols, suffix)
    if len(common_axes) < 3:
        st.warning(f"Not enough shared data for {title}")
        return
    labels = [c.replace("_", " ").title() for c in common_axes]
    fig = go.Figure()

    colors = px.colors.qualitative.Safe
    for i, (player_name, df) in enumerate(player_data.items()):
        values = [df[f"{col}_{suffix}"].iloc[0] for col in common_axes]
        color = colors[i % len(colors)]
        fig.add_trace(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=labels + [labels[0]],
                fill="toself",
                name=player_name,
                line=dict(
                    color=color,
                    width=3
                ),
                fillcolor=color,
                opacity=0.5
            )
        )

    fig.update_layout(
        title=title,
        polar=dict(radialaxis=dict(visible=True,range=[0, 100])),
        showlegend=True
    )
    st.plotly_chart(fig, use_container_width=True)