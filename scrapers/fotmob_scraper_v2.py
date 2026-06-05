import requests
from bs4 import BeautifulSoup
from typing import List, Set


class FotMobScraper:
    BASE_URL_BIO = "https://www.fotmob.com/api/data/playerData?id={}"
    BASE_URL_STATS = "https://www.fotmob.com/api/data/playerStats?playerId={}&seasonId={}&isFirstSeason=false"

    def __init__(self, cookies: dict = None, headers: dict = None):
        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.fotmob.com/"
        })

        if headers:
            self.session.headers.update(headers)

        if cookies:
            self.session.cookies.update(cookies)

    # -------------------------
    # API METHODS
    # -------------------------

    def get_player_bio(self, player_id: int):
        url = self.BASE_URL_BIO.format(player_id)
        headers = {
            "User-Agent": "Mozilla/5.0 ...",
            "Cookie": "turnstile_verified=1.1780660572.319566427e763eb12e5217eb11a6cfebfebbe5b7ba03e4a54947d97a76f94947"
        }
        r = self.session.get(url, timeout=15, headers=headers)

        if r.status_code != 200:
            raise Exception(f"Bio request failed: {r.status_code} - {r.text[:200]}")

        return r.json()

    def get_season_stats(self, player_id: int, competition_id: int):
        url = self.BASE_URL_STATS.format(player_id, competition_id)
        r = self.session.get(url, timeout=15)

        if r.status_code != 200:
            raise Exception(f"Stats request failed: {r.status_code} - {r.text[:200]}")

        return r.json()

    # -------------------------
    # HTML SCRAPING METHODS
    # -------------------------

    def get_teams_from_league(self, league_id: str) -> List[str]:
        url = f"https://www.fotmob.com/leagues/{league_id}"
        r = self.session.get(url, timeout=15)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "lxml")

        teams: Set[str] = set()

        for a in soup.find_all("a", href=True):
            if "/teams/" in a["href"]:
                teams.add("https://www.fotmob.com" + a["href"])

        return list(teams)

    def get_players_from_team(self, team_url: str) -> List[str]:
        team_url = team_url.replace("overview", "squad")

        r = self.session.get(team_url, timeout=15)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "lxml")

        players: Set[str] = set()

        squad_box = soup.find("div", class_="css-1qm9gpo-Column e152ovrx0")
        if not squad_box:
            return []

        for section in squad_box.find_all("div"):
            h2 = section.find("h2")
            if not h2:
                continue

            span = h2.find("span")
            if not span:
                continue

            position = span.get_text(strip=True).lower()

            if "coach" in position or "keepers" in position:
                continue

            for a in section.select("a[href^='/players/']"):
                parts = a["href"].split("/")
                if len(parts) > 2:
                    players.add(parts[2])

        return list(players)