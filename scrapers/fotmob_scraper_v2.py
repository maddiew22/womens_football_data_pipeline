import time
import requests
from bs4 import BeautifulSoup
from typing import List, Set
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


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

        self.session.cookies.set(
            "turnstile_verified",
            "1.1780766293.b95920c02dc2c35e1a2373c52af77e4e3ffad887cd888cd9a3c83e967b929dc5"
        )

        if headers:
            self.session.headers.update(headers)

        if cookies:
            self.session.cookies.update(cookies)

    def get_player_bio(self, player_id: int):
        url = self.BASE_URL_BIO.format(player_id)

        r = self.session.get(url, timeout=15)

        if r.status_code != 200:
            raise Exception(f"Bio request failed: {r.status_code} - {r.text[:200]}")

        return r.json()

    def get_season_stats(self, player_id: int, competition_id: int):
        url = self.BASE_URL_STATS.format(player_id, competition_id)

        r = self.session.get(url, timeout=15)

        if r.status_code != 200:
            raise Exception(f"Stats request failed: {r.status_code} - {r.text[:200]}")

        return r.json()


class TeamScraper:
    def __init__(self):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--remote-debugging-port=9222")
        options.page_load_strategy = "eager"

        self.driver = webdriver.Chrome(
            service=Service(),
            options=options
        )

        self.driver.set_page_load_timeout(60)
        self.driver.implicitly_wait(10)
        self.wait = WebDriverWait(self.driver, 30)

    def _wait_for_page(self):
        try:
            self.wait.until(
                lambda d: d.execute_script(
                    "return document.readyState"
                ) == "complete"
            )
        except TimeoutException:
            # If Chrome hangs waiting for resources, continue with whatever loaded.
            pass

    def _navigate(self, url, retries=2):
        for attempt in range(retries):
            try:
                self.driver.get(url)
                self._wait_for_page()
                return BeautifulSoup(self.driver.page_source, "lxml")
            except TimeoutException as exc:
                if attempt == retries - 1:
                    raise
                try:
                    self.driver.execute_script("window.stop();")
                except Exception:
                    pass
                time.sleep(2)
        raise TimeoutException(f"Could not load page: {url}")

    def close(self):
        self.driver.quit()

    def __del__(self):
        try:
            self.driver.quit()
        except Exception:
            pass

    def get_teams_from_league(self, league_id):
        url = f"https://www.fotmob.com/leagues/{league_id}"
        soup = self._navigate(url)

        teams = set()

        for a in soup.find_all("a", href=True):
            if "/teams/" in a["href"]:
                teams.add("https://www.fotmob.com" + a["href"])

        return list(teams)

    def get_players_from_team(self, team_url):
        team_url = team_url.replace("overview", "squad")

        soup = self._navigate(team_url)

        players = set()

        squad_box = soup.find("div", class_="css-1qm9gpo-Column e152ovrx0")

        if not squad_box:
            return []

        squad_subsections = squad_box.find_all("div")

        for section in squad_subsections:
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

    def get_comps_and_seaons(self, player_id):
        url = f"https://www.fotmob.com/en/players/{player_id}"
        soup = self._navigate(url)

        seasons = soup.find_all("optgroup")

        competitions = []

        for optgroup in seasons:
            season_group = optgroup.get("label", "").strip()

            comps = optgroup.find_all("option")

            for option in comps:
                competitions.append({
                    "season_group": season_group,
                    "competition": option.text.strip(),
                    "value": option.get("value")
                })

        return competitions