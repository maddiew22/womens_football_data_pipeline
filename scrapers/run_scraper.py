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
    9375: "Women's Champions League"
}

try:
    for league_id, league_name in LEAGUES.items():
        print(f"Scraping league: {league_name}")
        try:
            teams = team_scraper.get_teams_from_league(league_id)
        except Exception as e:
            print(f"Failed to get teams for league {league_name}: {e}")
            continue
        print(teams)
        team_player_map = {}

        for team_url in teams:
            print(team_url)
            try:
                team_players = team_scraper.get_players_from_team(team_url)
                team_player_map[team_url] = team_players
            except Exception as e:
                print(f"Failed to get players for team: {team_url}: {e}")
                continue
            
            for player_id in team_player_map[team_url]:
                try:
                    print(player_id)
                    bio = scraper.get_player_bio(player_id)
                    if bio:
                        db.save_raw_json(player_id, bio)

                    seasons = team_scraper.get_comps_and_seaons(player_id)
                    current_season_comps = [
                        season
                        for season in seasons
                        if str(season["value"]).startswith("0")
                    ]
                    for comp in current_season_comps:
                        comp_stats = scraper.get_season_stats(player_id, comp["value"])
                        if comp_stats:
                            db.save_raw_json_season_stats(player_id, comp["season_group"], comp["competition"], comp_stats)
                        
                except Exception as e:
                    print(e)
                    print(f"Failed to get data for player: {player_id}")
                    continue
finally:
    try:
        db.close()
    except Exception:
        pass
    try:
        team_scraper.close()
    except Exception:
        pass