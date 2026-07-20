import time
import requests
from bs4 import BeautifulSoup
from typing import List, Set
import cloudscraper

class SofascoreScraper:
    BASE_URL_BIO = "https://www.sofascore.com/api/v1/player/{}"
    BASE_URL_STATS = "https://www.sofascore.com/api/v1/player/{}/statistics"

    def __init__(self, cookies: dict = None, headers: dict = None):

        self.scraper = cloudscraper.create_scraper(
            browser={
                "browser": "chrome",
                "platform": "windows",
                "mobile": False
            }
        )

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.sofascore.com/",
            "Origin": "https://www.sofascore.com",
        }

        if headers:
            self.headers.update(headers)

        self.scraper.headers.update(self.headers)

        # Establish cookies/session
        home = self.scraper.get(
            "https://www.sofascore.com",
            timeout=15
        )

        print(
            "SofaScore homepage:",
            home.status_code
        )

        print(
            "Cookies:",
            self.scraper.cookies.get_dict()
        )

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