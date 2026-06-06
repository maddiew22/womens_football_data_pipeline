from fastapi import FastAPI
from databricks import sql
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")


def get_connection():
    return sql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN
    )

@app.get("/data")
def get_data(limit: int = 10):
    query = f"""
        SELECT *
        FROM workspace.fotmob.player_stats_processed
        LIMIT {limit}
    """

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query)

    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]

    df = pd.DataFrame(rows, columns=columns)

    cursor.close()
    conn.close()

    df = df.replace([np.nan, np.inf, -np.inf], None)

    return df.to_dict(orient="records")

@app.get("/players")
def get_players():
    query = """
        SELECT DISTINCT player_id, player_name
        FROM workspace.fotmob.player_overview_processed
    """

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query)

    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]

    df = pd.DataFrame(rows, columns=columns)

    cursor.close()
    conn.close()

    return df.to_dict(orient="records")