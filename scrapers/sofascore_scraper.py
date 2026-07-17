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
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.sofascore.com/",
        }
        if headers:
            self.headers.update(headers)
        self.scraper.headers.update(self.headers)

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

        r = self.scraper.get(url, timeout=15)
        
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