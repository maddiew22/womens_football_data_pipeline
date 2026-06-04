from scrapers.fotmob_scraper_v2 import FotMobScraper
from postgres_conn import PostgresDB
import pandas as pd
import os


db = PostgresDB(
    db_url=os.getenv("DB_URL")
)

db.connect()

scraper = FotMobScraper()

LEAGUES = {
    9227: "WSL",
    9134:"NWSL",
    9907: "Liga F",
    9676: "Frauen Bundesliga",
    9677: "Premiere League Feminine",
    10178: "Serie A Femminile",
}

for league_id, league_name in LEAGUES.items():
    print(f"Scraping league: {league_name}")
    teams = scraper.get_teams_from_league(league_id)
    team_player_map = {}

    for team_url in teams:
        team_players = scraper.get_players_from_team(team_url)
        team_player_map[team_url] = team_players

        for player_id in team_player_map[team_url]:
            print(player_id)
            bio = scraper.get_player_bio(player_id)
            db.save_raw_json(player_id, bio)

db.close()
scraper.close()