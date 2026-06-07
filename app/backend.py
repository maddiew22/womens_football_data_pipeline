from fastapi import FastAPI, HTTPException
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

def run_query(query: str):
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query)

        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(rows, columns=columns)
        df = df.astype(str)
        df = df.drop(columns=["penalties_awarded", "penalties_awarded_percentile", 
                              "penalty_goals", "penalty_goals_percentile", 
                              "xg_excl_penalty", "xg_excl_penalty_percentile", 
                              "penalties_awarded_per90", "penalty_goals_per90", 
                              "xg_excl_penalty_per90", "penalties_awarded_percentile_per90", 
                              "penalty_goals_percentile_per90", "xg_excl_penalty_percentile_per90",
                              "clean_sheets", "clean_sheets_per90", "clean_sheets_percentile", "clean_sheets_percentile_per90",
                              "blocked_scoring_attempt", "blocked_scoring_attempt_per90", "blocked_scoring_attempt_percentile", "blocked_scoring_attempt_percenitle_per90"], errors="ignore")
        df = df.replace([np.nan, np.inf, -np.inf], None)
        return df.to_dict(orient="records")

    except Exception as e:
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