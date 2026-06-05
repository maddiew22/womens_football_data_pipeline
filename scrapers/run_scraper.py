from scrapers.fotmob_scraper_v2 import FotMobScraper, TeamScraper
from postgres_conn import PostgresDB
import pandas as pd
import os


db = PostgresDB(
    db_url=os.getenv("DB_URL")
)

db.connect()

scraper = FotMobScraper()
team_scraper = TeamScraper()

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
    teams = team_scraper.get_teams_from_league(league_id)
    print(teams)
    team_player_map = {}

    for team_url in teams:
        print(team_url)
        try:
            team_players = team_scraper.get_players_from_team(team_url)
            team_player_map[team_url] = team_players
        except:
            print(f"Failed to get players for team: {team_url}")
            continue
        
        for player_id in team_player_map[team_url]:
            try:
                print(player_id)
                bio = scraper.get_player_bio(player_id)
                db.save_raw_json(player_id, bio)

                seasons = team_scraper.get_comps_and_seaons(player_id)
                for season in seasons:
                    comp_stats = scraper.get_season_stats(player_id, season["value"])
                    db.save_raw_json_season_stats(player_id, season["season_group"], season["competition"], comp_stats)
                    
            except:
                print(f"Failed to get data for player: {player_id}")
                continue

db.close()
scraper.close()