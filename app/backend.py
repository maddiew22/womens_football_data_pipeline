from fastapi import FastAPI, HTTPException, Query
from typing import Optional, List
from databricks import sql
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv

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
        df = df.astype(str)

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

        df = df.replace([np.nan, np.inf, -np.inf], None)

        return df.to_dict(orient="records")

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
        FROM workspace.fotmob.player_stats_processed
        LIMIT {limit}
    """
    return run_query(query)

@app.get("/players")
def get_players():
    query = """
        SELECT DISTINCT player_id, player_name
        FROM workspace.fotmob.player_overview_processed
    """
    return run_query(query)


@app.get("/players/bio/{player_id}")
def get_player_bio(player_id: int):
    query = f"""
        SELECT *
        FROM workspace.fotmob.player_overview_processed
        WHERE player_id = {player_id}
    """
    return run_query(query)

@app.get("/players/stats/{player_id}")
def get_player_stats(player_id: int):
    query = f"""
        SELECT *
        FROM workspace.fotmob.player_stats_processed
        WHERE player_id = {player_id}
    """
    return run_query(query)

@app.get("/competitions")
def get_competitions():
    query = f"""
        SELECT DISTINCT
            competition
        FROM workspace.fotmob.player_stats_processed
    """
    return run_query(query)

@app.get("/available_stats")
def get_available_stats():
    query = """
        SELECT column_name
        FROM workspace.information_schema.columns
        WHERE table_name = 'player_stats_processed'
          AND column_name NOT IN ('player_id', 'season', 'competition')
    """
    return run_query(query)


AVG_KEYWORDS = ["per90", "accuracy", "rate"]
def get_agg(stat):
    stat_l = stat.lower()
    if any(k in stat_l for k in AVG_KEYWORDS):
        return "AVG"
    return "SUM"

@app.get("/leaderboards/{stat}")
def get_leaderboards(
    stat: str,
    competition: Optional[List[str]] = Query(None)
):
    
    agg_expr = f"{get_agg(stat)}(stats.{stat})"

    query = f"""
        SELECT
            bio.player_name,
            {agg_expr} AS value,
            bio.primary_position, 
            COLLECT_SET(stats.competition) AS competitions
        FROM workspace.fotmob.player_stats_processed AS stats
        JOIN workspace.fotmob.player_overview_processed AS bio
            ON stats.player_id = bio.player_id
        WHERE stats.season = YEAR(CURRENT_DATE)
    """

    params = None

    if competition:
        cleaned = [
            c.strip().lower().replace("’", "'")
            for c in competition
            if c
        ]

        if cleaned:
            placeholders = ", ".join(["?"] * len(cleaned))

            query += f"""
                AND LOWER(TRIM(REPLACE(stats.competition, '’', '''')))
                IN ({placeholders})
            """

            params = cleaned

    query += """
        GROUP BY
            bio.player_name,
            stats.player_id,
            bio.primary_position
        ORDER BY value DESC
        LIMIT 1000
    """

    return run_query(query, params)

@app.get("/statsbomb/competitions/{player}")
def get_statsbomb_competitions(player: str):
    query = """
    SELECT DISTINCT competition_name 
    FROM workspace.fotmob.processed_player_matches
    WHERE LOWER(COALESCE(nickname, player_name)) = LOWER(?)
    """
    return run_query(query, params=[player])


@app.get("/statsbomb_matches/{competition}/{player}")
def get_statsbomb_player_matches(player: str, competition: str):
    """Get all matches for a player by nickname or player name."""
    query = """
    SELECT DISTINCT 
        match_id, 
        match_date, 
        competition_name, 
        season_name,
        team_name,
        COALESCE(nickname, player_name) as display_name
    FROM workspace.fotmob.processed_player_matches 
    WHERE LOWER(competition_name) = LOWER(?)
      AND LOWER(COALESCE(nickname, player_name)) = LOWER(?)
    ORDER BY match_date DESC
    """
    return run_query(query, params=[competition, player])


@app.get("/statsbomb_passes/{match_id}/{player}")
def get_statsbomb_passes(match_id: int, player: str):
    """Get pass data for a player in a specific match (passes made BY or TO the player)."""
    query = """
    SELECT DISTINCT
        pl.player,
        pl.pass_recipient,
        pl.start_x,
        pl.start_y,
        pl.end_x,
        pl.end_y,
        pl.pass_outcome,
        pl.pass_type,
        pl.team,
        pl.minute,
        pl.second
    FROM workspace.fotmob.processed_pass_locations pl
    LEFT JOIN workspace.fotmob.processed_player_matches pm_passer
        ON pl.match_id = pm_passer.match_id 
        AND LOWER(pl.player) = LOWER(pm_passer.player_name)
    LEFT JOIN workspace.fotmob.processed_player_matches pm_recipient
        ON pl.match_id = pm_recipient.match_id 
        AND LOWER(pl.pass_recipient) = LOWER(pm_recipient.player_name)
    WHERE pl.match_id = ?
      AND (
        LOWER(COALESCE(pm_passer.nickname, pm_passer.player_name)) = LOWER(?)
        OR LOWER(COALESCE(pm_recipient.nickname, pm_recipient.player_name)) = LOWER(?)
      )
    """
    return run_query(query, params=[match_id, player, player])


@app.get("/statsbomb_events/{match_id}/{player}")
def get_statsbomb_events(match_id: int, player: str):
    """Get event location data for a player in a specific match."""
    query = """
    SELECT
        el.player,
        el.team,
        el.type,
        el.minute,
        el.second,
        el.x,
        el.y
    FROM workspace.fotmob.processed_event_locations el
    INNER JOIN workspace.fotmob.processed_player_matches pm
        ON el.match_id = pm.match_id 
        AND LOWER(el.player) = LOWER(pm.player_name)
    WHERE el.match_id = ?
      AND LOWER(COALESCE(pm.nickname, pm.player_name)) = LOWER(?)
    """
    return run_query(query, params=[match_id, player])