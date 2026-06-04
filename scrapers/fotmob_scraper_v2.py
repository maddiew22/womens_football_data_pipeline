import time
from click import option
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import numpy as np
from bs4 import BeautifulSoup


class FotMobScraper:
    BASE_URL_BIO = "https://www.fotmob.com/api/data/playerData?id={}"
    BASE_URL_STATS = "https://www.fotmob.com/api/data/playerStats?playerId={}&seasonId={}&isFirstSeason=false"

    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)

    def get_player_bio(self, player_id):
        url = self.BASE_URL_BIO.format(player_id)
        json = self.driver.get(url)
        time.sleep(5)
        return json
   
    def get_season_stats(self, player_id, competition_id):
        url = self.BASE_URL_STATS.format(player_id, competition_id)
        json = self.driver.get(url)
        time.sleep(5)
        return json
    

    def get_teams_from_league(self, league_id):
        url = f"https://www.fotmob.com/leagues/{league_id}"
        self.driver.get(url)
        time.sleep(5)

        soup = BeautifulSoup(self.driver.page_source, "lxml")
        teams = set()

        for a in soup.find_all("a", href=True):
            if "/teams/" in a["href"]:
                teams.add("https://www.fotmob.com" + a["href"])

        return list(teams)
    
    def get_players_from_team(self, team_url):
        team_url = team_url.replace("overview", "squad")
        self.driver.get(team_url)
        soup = BeautifulSoup(self.driver.page_source, "lxml")

        players = set()
        squad_box = soup.find("div", class_="css-1qm9gpo-Column e152ovrx0")
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

                # collect player links in this section only
                for a in section.select("a[href^='/players/']"):
                    parts = a["href"].split("/")
                    if len(parts) > 2:
                        players.add(parts[2])

        return list(players)

    def close(self):
        self.driver.quit()

    def __del__(self):
        try:
            self.driver.quit()
        except:
            pass