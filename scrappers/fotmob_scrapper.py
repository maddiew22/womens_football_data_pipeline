import time
import pandas as pd
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class FotMobScraper:
    BASE_URL = "https://www.fotmob.com/en/players/{}"

    def __init__(self, headless=True):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--start-maximized")

        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)

   
    def _load_page(self, player_id):
        url = self.BASE_URL.format(player_id)
        self.driver.get(url)
        time.sleep(5)
        return BeautifulSoup(self.driver.page_source, "lxml")

    def close(self):
        self.driver.quit()

    # Player bio and info
    def get_player_bio(self, player_id):
        soup = self._load_page(player_id)

        rows = []

        player_name = soup.find("h1")
        if player_name:
            rows.append({"stat": "Name", "value": player_name.text.strip()})

        bio = soup.find("div", class_="css-nlprju-PlayerBioCSS e1sx8s6x0")
        if bio:
            stat_blocks = bio.find_all("div", class_="css-to3w1c-StatValueCSS e1e6xf3b2")

            for block in stat_blocks:
                value = block.get_text(strip=True)
                parent = block.find_parent()

                title_tag = parent.find("div", class_="css-tp32vr-StatTitleCSS e1e6xf3b1")
                title = title_tag.get_text(strip=True) if title_tag else None

                rows.append({"stat": title, "value": value})

        position_block = soup.find("div", class_="css-1y1g69o-PositionSectionCSS e1sqdo1t7")
        if position_block:
            pos_tag = position_block.find("div", class_="css-1g41csj-PositionsCSS e1sqdo1t6")
            position = pos_tag.get_text(strip=True) if pos_tag else None
            rows.append({"stat": "Primary Position", "value": position})

        return pd.DataFrame(rows)

    # Current season overview
    def get_current_season_overview(self, player_id):
        soup = self._load_page(player_id)

        stats_box = soup.find("div", class_="css-4yroh7-StatsContainer elcfuwp1")
        if not stats_box:
            return pd.DataFrame()

        rows = []
        stat_blocks = stats_box.find_all("div", class_="css-48dyyr-StatBox elcfuwp6")

        for block in stat_blocks:
            value_tag = block.find("div", class_="css-170fd60-StatValue elcfuwp5")
            title_tag = block.find("span", class_="css-1xy07gm-StatTitle elcfuwp4")

            value = value_tag.get_text(strip=True) if value_tag else None
            title = title_tag.get_text(strip=True) if title_tag else None

            if title == "Rating":
                rating_block = block.find("div", class_="css-phu8uv-PlayerRatingCSS e1xb9tyd0")
                rating = rating_block.find("span") if rating_block else None
                value = rating.get_text(strip=True) if rating else value

            rows.append({"stat": title, "value": value})

        return pd.DataFrame(rows)

    # Season stats (normal + per 90)
    def get_current_season_stats(self, player_id):
        url = self.BASE_URL.format(player_id)
        self.driver.get(url)

        wait = self.wait

        first_stat_elem = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.css-13fpglj-StatValue.e1fqvhy52 span")
            )
        )
        first_stat_value = first_stat_elem.text

        html_no_filters = self.driver.page_source

        button = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, ".css-bmwvkt-FilterButton")
            )
        )

        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});",
            button
        )
        self.driver.execute_script("arguments[0].click();", button)

        # select Per 90
        per90_option = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[contains(text(), 'Per 90')]")
            )
        )
        self.driver.execute_script("arguments[0].click();", per90_option)

        wait.until(
            lambda d: d.find_element(
                By.CSS_SELECTOR,
                "div.css-13fpglj-StatValue.e1fqvhy52 span"
            ).text != first_stat_value
        )

        time.sleep(1) 

        html_with_filters = self.driver.page_source

        soup_no_filters = BeautifulSoup(html_no_filters, "lxml")
        soup_with_filters = BeautifulSoup(html_with_filters, "lxml")

        rows = []

        datasets = [
            ("base", soup_no_filters),
            ("per90", soup_with_filters)
        ]

        for label, soup in datasets:
            block = soup.find(
                "div",
                class_="css-15lw8xy-SeasonPerformanceCSS e1fqvhy58"
            )

            if not block:
                return pd.DataFrame()

            stat_items = block.find_all(
                "div",
                class_="css-1v73fp6-StatItemCSS e1fqvhy50"
            )

            for group in stat_items:
                title_tag = group.find("span", class_="css-1u1ywg2-StatTitle e1fqvhy51")
                value_tag = group.find("div", class_="css-13fpglj-StatValue e1fqvhy52")

                title = title_tag.get_text(strip=True) if title_tag else None
                value = value_tag.get_text(strip=True) if value_tag else None

                rows.append({
                    "stat": title,
                    "value": value,
                    "type": label 
                })
        return pd.DataFrame(rows)
    
    def __del__(self):
        try:
            self.driver.quit()
        except:
            pass