import time
import requests
from bs4 import BeautifulSoup
from typing import List, Set
import cloudscraper

class SofascoreScraper:
    BASE_URL_BIO = "https://www.sofascore.com/api/v1/player/{}"
    BASE_URL_STATS = "https://www.sofascore.com/api/v1/player/{}/statistics"

    def __init__(self, cookies: dict = None, headers: dict = None):
        self.scraper = cloudscraper.create_scraper()
        
    def get_player_bio(self, player_id: int):
        url = self.BASE_URL_BIO.format(player_id)

        r = self.scraper.get(url, timeout=15)

        if r.status_code != 200:
            raise Exception(f"Bio request failed: {r.status_code} - {r.text[:200]}")

        return r.json()

    def get_season_stats(self, player_id: int):
        url = self.BASE_URL_STATS.format(player_id)

        r = self.scraper.get(url, timeout=15)

        if r.status_code != 200:
            raise Exception(f"Stats request failed: {r.status_code} - {r.text[:200]}")

        return r.json()
    
    def get_league_seasons(self, league_id: int):
        url = f"https://www.sofascore.com/api/v1/unique-tournament/{league_id}/seasons"

        # print("URL:", url)
        # print("Headers:", self.scraper.headers)
        # print("Cookies:", self.scraper.cookies)

        r = self.scraper.get(url, timeout=15)

        # print("Status:", r.status_code)
        # print("Response:", r.text[:300])
        return r.json()
    
    def get_league_season_standings(self, league_id: int, season_id: int):
        url = f"https://www.sofascore.com/api/v1/unique-tournament/{league_id}/season/{season_id}/standings/total"

        r = self.scraper.get(url, timeout=15)

        if r.status_code != 200:
            raise Exception(f"League season request failed: {r.status_code} - {r.text[:200]}")

        return r.json()
    
    def get_team_players(self, team_id: int):
        url = f"https://www.sofascore.com/api/v1/team/{team_id}/players"

        r = self.scraper.get(url, timeout=15)

        if r.status_code != 200:
            raise Exception(f"Team request failed: {r.status_code} - {r.text[:200]}")

        return r.json()