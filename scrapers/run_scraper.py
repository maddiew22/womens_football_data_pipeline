from scrapers.fotmob_scraper import FotMobScraper
from postgres_conn import PostgresDB
import pandas as pd
import os

def main():
    db = PostgresDB(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=int(os.getenv("DB_PORT", 5432))
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
                bio = scraper.get_player_bio(player_id)
                season_overview = scraper.get_current_season_overview(player_id)
                db.save_player_fotmob_data(bio, season_overview, season_stats_df=pd.DataFrame())
    db.close()
    scraper.close()

if __name__ == "__main__":
    main()