from fastapi import FastAPI, HTTPException, Query
from typing import Optional, List
from databricks import sql
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
import unicodedata
import re

load_dotenv()

SERVER_HOSTNAME = os.getenv("DATABRICKS_HOST")
ACCESS_TOKEN = os.getenv("DATABRICKS_TOKEN")

if not SERVER_HOSTNAME:
    raise ValueError("Missing DATABRICKS_HOST")

if not ACCESS_TOKEN:
    raise ValueError("Missing DATABRICKS_TOKEN")

HTTP_PATH = "/sql/1.0/warehouses/fc1b55dc6c5eee1c"

app = FastAPI()

DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")

import numpy as np

def make_json_safe(value):
    # Handle numpy arrays / Databricks arrays first
    if isinstance(value, np.ndarray):
        return value.tolist()

    # Handle lists
    if isinstance(value, list):
        return [make_json_safe(v) for v in value]

    # Handle dictionaries
    if isinstance(value, dict):
        return {k: make_json_safe(v) for k, v in value.items()}

    # Handle missing values safely
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    # Convert numpy scalar types
    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        return float(value)

    return value

def get_connection():
    return sql.connect(
        server_hostname=SERVER_HOSTNAME,
        http_path=HTTP_PATH,
        access_token=ACCESS_TOKEN
    )

def run_query(query: str, params=None):
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        df = pd.DataFrame(rows, columns=columns)

        df = df.drop(
            columns=[
                "penalties_awarded", "penalties_awarded_percentile",
                "penalty_goals", "penalty_goals_percentile",
                "xg_excl_penalty", "xg_excl_penalty_percentile",
                "penalties_awarded_per90", "penalty_goals_per90",
                "xg_excl_penalty_per90", "penalties_awarded_percentile_per90",
                "penalty_goals_percentile_per90", "xg_excl_penalty_percentile_per90",
                "clean_sheets", "clean_sheets_per90",
                "clean_sheets_percentile", "clean_sheets_percentile_per90",
                "blocked_scoring_attempt", "blocked_scoring_attempt_per90",
                "blocked_scoring_attempt_percentile",
                "blocked_scoring_attempt_percenitle_per90"
            ],
            errors="ignore"
        )
        records = df.to_dict(orient="records")
        records = [
            {
                key: make_json_safe(value)
                for key, value in row.items()
            }
            for row in records
        ]
        return records

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ENDPOINTS
@app.get("/data")
def get_data(limit: int = 10):
    query = f"""
        SELECT *
        FROM workspace.fotmob.player_stats_gold
        LIMIT {limit}
    """
    return run_query(query)

@app.get("/players")
def get_players():
    query = """
        SELECT player_id, player_name FROM workspace.fotmob.player_lookup
    """
    return run_query(query)


@app.get("/players/bio/{player_id}")
def get_player_bio(player_id: int):
    query = f"""
        SELECT *
        FROM workspace.fotmob.player_overview_gold
        WHERE player_id = {player_id}
    """
    return run_query(query)

@app.get("/players/stats/{player_id}")
def get_player_stats(player_id: int):
    query = f"""
        SELECT *
        FROM workspace.fotmob.player_stats_gold
        WHERE player_id = {player_id}
    """
    return run_query(query)

@app.get("/{season}/competitions")
def get_competitions(season):
    query = f"""
        SELECT DISTINCT
            competition
        FROM workspace.fotmob.player_stats_gold
        WHERE season = {season}
    """
    return run_query(query)

@app.get("/available_stats")
def get_available_stats():
    query = """
        SELECT column_name
        FROM workspace.information_schema.columns
        WHERE table_name = 'player_stats_gold'
          AND column_name NOT IN ('player_id', 'season', 'competition')
    """
    return run_query(query)

@app.get("/seasons")
def get_seasons():
    query = f"""
        SELECT DISTINCT season
        FROM workspace.fotmob.player_stats_gold
    """
    return run_query(query)

@app.get("/players/stats/shot_data/{player_id}")
def get_player_shot_stats(
    player_id: int,
    season: Optional[str] = Query(None),
    competition: Optional[str] = Query(None),
):
    query = f"""
        SELECT *
        FROM workspace.fotmob.shot_details
        WHERE player_id = {player_id}
    """
    if season:
        query += f" AND season = '{season}'"
    if competition:
        query += f" AND competition = '{competition}'"
    return run_query(query)

@app.get("/players/stats/shot_overview/{player_id}")
def get_player_shot_stats_overview(
    player_id: int,
    season: Optional[str] = Query(None),
    competition: Optional[str] = Query(None),
):
    query = f"""
        SELECT *
        FROM workspace.fotmob.player_shot_stats
        WHERE player_id = {player_id}
    """
    if season:
        query += f" AND season = '{season}'"
    if competition:
        query += f" AND competition = '{competition}'"
    return run_query(query)

AVG_KEYWORDS = ["per90", "accuracy", "rate"]
def get_agg(stat):
    stat_l = stat.lower()
    if any(k in stat_l for k in AVG_KEYWORDS):
        return "AVG"
    return "SUM"

@app.get("/leaderboards/{season}/{stat}")
def get_leaderboards(season, stat):
    comps_to_exclude = [
        "WSL 2", "NWSL Challenge Cup", "A-League Women",
        "NWSL Fall Series Northeast", "NWSL Fall Series West",
        "NWSL Fall Series South", "Concacaf W Qualifiers",
        "W-League", "Summer Olympics Women"
    ]

    agg_expr = f"{get_agg(stat)}(stats.{stat})"

    exclude_list = ", ".join([f"'{c}'" for c in comps_to_exclude])

    query = f"""
        SELECT
            bio.player_name,
            stats.{stat},
            bio.primary_position,
            stats.competition,
            stats.minutes_played
        FROM workspace.fotmob.player_stats_gold AS stats
        JOIN workspace.fotmob.player_overview_gold AS bio
            ON stats.player_id = bio.player_id
        WHERE stats.season = {season}
        AND stats.competition NOT IN ({exclude_list})
        ORDER BY {stat} DESC
        LIMIT 5000
    """

    return run_query(query)

def strip_accents(text: str) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))

def normalize_name(name: str) -> set[str]:
    name = strip_accents(name)
    return {
        token
        for token in re.findall(r"[a-z]+", name.lower())
    }

def names_match(search_name: str, candidate_name: str) -> bool:
    search_tokens = normalize_name(search_name)
    candidate_tokens = normalize_name(candidate_name)

    # Exact match
    if search_tokens == candidate_tokens:
        return True

    # At least 2 shared tokens
    return len(search_tokens & candidate_tokens) >= 2

def resolve_player(player: str) -> str:
    query = """
    SELECT DISTINCT
        player_name,
        nickname
    FROM workspace.fotmob.processed_player_matches
    """

    players = run_query(query)

    # Exact match first
    for row in players:
        player_name = row["player_name"]
        nickname = row.get("nickname")

        if player_name and player.lower() == player_name.lower():
            return player_name

        if nickname and player.lower() == nickname.lower():
            return player_name

    matches = []

    for row in players:
        player_name = row["player_name"]
        nickname = row.get("nickname")

        if player_name and names_match(player, player_name):
            matches.append(player_name)
            continue

        if nickname and names_match(player, nickname):
            matches.append(player_name)

    matches = list(dict.fromkeys(matches))

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        search_tokens = normalize_name(player)

        return max(
            matches,
            key=lambda name: len(
                search_tokens & normalize_name(name)
            )
        )

    return player

@app.get("/statsbomb/competitions/{player}")
def get_statsbomb_competitions(player: str):
    resolved_player = resolve_player(player)
    print(f"INPUT={player}")
    print(f"RESOLVED={resolved_player}")
    query = """
    SELECT DISTINCT competition_name
    FROM workspace.fotmob.processed_player_matches
    WHERE LOWER(player_name) = LOWER(?)
    ORDER BY competition_name
    """

    return run_query(query, params=[resolved_player])

@app.get("/statsbomb_matches/{competition}/{player}")
def get_statsbomb_player_matches(player: str, competition: str):
    resolved_player = resolve_player(player)
    
    query = """
    SELECT DISTINCT
        match_id,
        match_date,
        competition_name,
        season_name,
        team_name,
        COALESCE(nickname, player_name) AS display_name
    FROM workspace.fotmob.processed_player_matches
    WHERE LOWER(competition_name) = LOWER(?)
      AND LOWER(player_name) = LOWER(?)
    ORDER BY match_date DESC
    """

    return run_query(
        query,
        params=[competition, resolved_player]
    )

@app.get("/statsbomb_passes/{match_id}/{player}")
def get_statsbomb_passes(match_id: int, player: str):
    resolved_player = resolve_player(player)

    query = """
    SELECT DISTINCT
        player,
        pass_recipient,
        start_x,
        start_y,
        end_x,
        end_y,
        pass_outcome,
        pass_type,
        team,
        minute,
        second
    FROM workspace.fotmob.processed_pass_locations
    WHERE match_id = ?
      AND (
          LOWER(player) = LOWER(?)
          OR LOWER(pass_recipient) = LOWER(?)
      )
    """

    return run_query(
        query,
        params=[
            match_id,
            resolved_player,
            resolved_player
        ]
    )

@app.get("/statsbomb_events/{match_id}/{player}")
def get_statsbomb_events(match_id: int, player: str):
    resolved_player = resolve_player(player)

    query = """
    SELECT
        player,
        team,
        type,
        minute,
        second,
        x,
        y
    FROM workspace.fotmob.processed_event_locations
    WHERE match_id = ?
      AND LOWER(player) = LOWER(?)
    """

    return run_query(
        query,
        params=[
            match_id,
            resolved_player
        ]
    )