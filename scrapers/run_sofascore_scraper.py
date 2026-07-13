from scrapers.sofascore_scraper import SofascoreScraper
from postgres_conn import PostgresDB
import pandas as pd
import os

import sys
import scrapers.sofascore_scraper as ss

db = PostgresDB(
    db_url=os.getenv("DB_URL")
)

db.connect()

scraper = SofascoreScraper()

LEAGUES = {
    18653: "WE-League",
    214: "Damallsvenskan",
    10257: "Brasileirão Série A1",
}

try:
    for league_id, league_name in LEAGUES.items():
        print(f"Scraping league: {league_name}")
        try:
            league_seasons = scraper.get_league_seasons(league_id)
            season_id = league_seasons["seasons"][0]["id"]
            raw_league_teams = scraper.get_league_season_standings(league_id, season_id)
   
            standings = raw_league_teams["standings"][0]["rows"]
            teams = [team["team"]["id"] for team in standings]

        except Exception as e:
            print(f"Failed to get teams for league {league_name}: {e}")
            continue
        print(teams)


        for team in teams:
            try:
                team_players = scraper.get_team_players(team)
                players = team_players["players"]
                for player in players:
                    player_id = player["player"]["id"]
                    player_overview = scraper.get_player_bio(player_id)
                    player_stats = scraper.get_season_stats(player_id)
                    db.save_raw_sofascore_json(player_id, player_overview)
                    db.save_raw_sofascore_json_season_stats(player_id, player_stats)
            except Exception as e:
                print(f"Failed to get players for team: {team}: {e}")
                continue
finally:
    try:
        db.close()
    except Exception:
        pass