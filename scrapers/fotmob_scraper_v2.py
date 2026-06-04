import time
from click import option
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import numpy as np


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

    def close(self):
        self.driver.quit()

    def __del__(self):
        try:
            self.driver.quit()
        except:
            pass