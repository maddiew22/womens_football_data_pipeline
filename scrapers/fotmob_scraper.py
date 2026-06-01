import time
from click import option
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import numpy as np


class FotMobScraper:
    BASE_URL = "https://www.fotmob.com/en/players/{}"

    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)

   
    def _load_page(self, player_id):
        url = self.BASE_URL.format(player_id)
        self.driver.get(url)
        time.sleep(5)
        return BeautifulSoup(self.driver.page_source, "lxml")

    def close(self):
        self.driver.quit()

    def __del__(self):
        try:
            self.driver.quit()
        except:
            pass

    # Player bio and info
    def get_player_bio(self, player_id):
        expected_cols = ["player_id", "Name", "Birthdate", "Height", "Primary Position", "Preferred foot", "Club"]

        soup = self._load_page(player_id)

        data = {}
        data["player_id"] = player_id

        # Name
        player_name = soup.find("h1")
        if player_name:
            data["Name"] = player_name.text.strip()

        # Club 
        club_block = soup.find("div", class_="css-1l2h5po-NameAndTeam e1vg4tga4")
        team_link = club_block.find("a") if club_block else None
        if team_link and team_link.has_attr("href"):
            href = team_link["href"]
            data["Club"] = href.split("/")[-1].replace("-", " ").title()

        # Bio stats
        bio = soup.find("div", class_="css-nlprju-PlayerBioCSS e1sx8s6x0")
        if bio:
            stat_blocks = bio.find_all("div", class_="css-to3w1c-StatValueCSS e1e6xf3b2")

            for block in stat_blocks:
                value = block.get_text(strip=True)
                parent = block.find_parent()

                title_tag = parent.find("div", class_="css-tp32vr-StatTitleCSS e1e6xf3b1")
                title = title_tag.get_text(strip=True) if title_tag else None

                if not title:
                    continue

                if title == "Height":
                    cleaned = value.replace("cm", "").strip()
                    try:
                        value = float(cleaned) if cleaned else None
                    except:
                        value = None

                if title and any(month in title for month in [
                    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
                ]):
                    data[title] = title
                    data["Birthdate"] = datetime.strptime(data[title], "%b %d, %Y").date() if data[title] else None
                    del data[title]
                else:
                    data[title] = value

        # Position
        position_block = soup.find("div", class_="css-1y1g69o-PositionSectionCSS e1sqdo1t7")
        if position_block:
            pos_tag = position_block.find("div", class_="css-1g41csj-PositionsCSS e1sqdo1t6")
            position = pos_tag.get_text(strip=True) if pos_tag else None
            data["Primary Position"] = position
        df = pd.DataFrame([data])
        for col in expected_cols:
            if col not in df.columns:
                df[col] = np.nan
        return df

    # Current season overview
    def get_current_season_overview(self, player_id):
        expected_cols = ['Goals', 'Assists', 'Started', 'Matches', 'Minutes played', 'Rating',
       'player_id', 'season']
        
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
        df = pd.DataFrame(rows)
        df = df.set_index("stat").T
        df["player_id"] = player_id
        df["season"] = datetime.now().year
        for col in expected_cols:
            if col not in df.columns:
                df[col] = np.nan
        return df

    # Season stats (normal + per 90)
    def get_current_season_stats(self, player_id):
        expected_stats = ['Accurate long balls', 'Accurate long balls %',
       'Accurate long balls %_per90', 'Accurate long balls_per90',
       'Aerial duels won', 'Aerial duels won %', 'Aerial duels won %_per90',
       'Aerial duels won_per90', 'Assists', 'Assists_per90', 'Chances created', 
       'Chances created_per90','Clean sheets', 'Clean sheets_per90', 'Clearances', 
       'Clearances_per90','Defensive contributions', 'Defensive contributions_per90',
       'Dispossessed', 'Dispossessed_per90', 'Dribbled past',
       'Dribbled past_per90', 'Duels won', 'Duels won %', 'Duels won %_per90',
       'Duels won_per90', 'Expected assists (xA)',
       'Expected assists (xA)_per90', 'Expected goals (xG)',
       'Expected goals (xG)_per90', 'Fouls committed', 'Fouls committed_per90',
       'Fouls won', 'Fouls won_per90', 'Goals',
       'Goals conceded while on pitch', 'Goals conceded while on pitch_per90',
       'Goals_per90', 'Interceptions', 'Interceptions_per90',
       'Possession won final 3rd', 'Possession won final 3rd_per90',
       'Recoveries', 'Recoveries_per90', 'Red cards', 'Red cards_per90',
       'Shots', 'Shots on target', 'Shots on target_per90', 'Shots_per90',
       'Successful crosses', 'Successful crosses %',
       'Successful crosses %_per90', 'Successful crosses_per90',
       'Successful dribbles', 'Successful dribbles %',
       'Successful dribbles %_per90', 'Successful dribbles_per90',
       'Successful passes', 'Successful passes %', 'Successful passes %_per90',
       'Successful passes_per90', 'Tackles', 'Tackles_per90', 'Touches',
       'Touches in opposition box', 'Touches in opposition box_per90',
       'Touches_per90', 'Yellow cards', 'Yellow cards_per90',
       'xG against while on pitch', 'xG against while on pitch_per90',
       'xG on target (xGOT)', 'xG on target (xGOT)_per90', 'player_id',
       'season']

        url = self.BASE_URL.format(player_id)
        self.driver.get(url)

        wait = self.wait

        generic_soup = self._load_page(player_id)
        stats_box = generic_soup.find("div", class_="css-15lw8xy-SeasonPerformanceCSS e1fqvhy58")
        if not stats_box:
            return pd.DataFrame()

        league_selector = generic_soup.find("div", class_="css-1odgbvs-SeasonSelectCSS e15abtql0")
        if league_selector:
            select = league_selector.find("select")
            if select:
                current_comp = select.get("aria-label", "").replace("Selected: ", "")

    

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
                value = value_tag.get_text(strip=True) if value_tag else np.nan

                rows.append({
                    "stat": title,
                    "value": value,
                    "type": label 
                })

        df = pd.DataFrame(rows)

        df["stat"] = df.apply(
            lambda r: f"{r['stat']}_per90" if r["type"] == "per90" else r["stat"],
            axis=1
        )

        df = df.pivot_table(
            index=df.index // len(df),
            columns="stat",
            values="value",
            aggfunc="first"
        ).reset_index(drop=True)

        for stat in expected_stats:
            if stat not in df.columns:
                df[stat] = np.nan

        df["Accurate long balls %"] = (
            df["Accurate long balls %"]
            .str.replace("%", "", regex=False)
            .astype(float) / 100 if df["Accurate long balls %"].notna().any() else np.nan
        )
        df["Aerial duels won %"] = (
            df["Aerial duels won %"]
            .str.replace("%", "", regex=False)
            .astype(float) / 100 if df["Aerial duels won %"].notna().any() else np.nan
        )
        df["Duels won %"] = (
            df["Duels won %"]
            .str.replace("%", "", regex=False)
            .astype(float) / 100 if df["Duels won %"].notna().any() else np.nan
        )
        df["Successful passes %"] = (
            df["Successful passes %"]
            .str.replace("%", "", regex=False)
            .astype(float) / 100 if df["Successful passes %"].notna().any() else np.nan
        )
        df["Successful dribbles %"] = (
            df["Successful dribbles %"]
            .str.replace("%", "", regex=False)
            .astype(float) / 100 if df["Successful dribbles %"].notna().any() else np.nan
        )
        df["Successful crosses %"] = (
            df["Successful crosses %"]
            .str.replace("%", "", regex=False)
            .astype(float) / 100 if df["Successful crosses %"].notna().any() else np.nan
        )

        df["Accurate long balls %_per90"] = (
            df["Accurate long balls %_per90"]
            .str.replace("%", "", regex=False)
            .astype(float) / 100 if df["Accurate long balls %_per90"].notna().any() else np.nan
        )
        df["Aerial duels won %_per90"] = (
            df["Aerial duels won %_per90"]
            .str.replace("%", "", regex=False)
            .astype(float) / 100 if df["Aerial duels won %_per90"].notna().any() else np.nan
        )
        df["Duels won %_per90"] = (
            df["Duels won %_per90"]
            .str.replace("%", "", regex=False)
            .astype(float) / 100 if df["Duels won %_per90"].notna().any() else np.nan
        )
        df["Successful passes %_per90"] = (
            df["Successful passes %_per90"]
            .str.replace("%", "", regex=False)
            .astype(float) / 100 if df["Successful passes %_per90"].notna().any() else np.nan
        )
        df["Successful dribbles %_per90"] = (
            df["Successful dribbles %_per90"]
            .str.replace("%", "", regex=False)
            .astype(float) / 100 if df["Successful dribbles %_per90"].notna().any() else np.nan
        )
        df["Successful crosses %_per90"] = (
            df["Successful crosses %_per90"]
            .str.replace("%", "", regex=False)
            .astype(float) / 100 if df["Successful crosses %_per90"].notna().any() else np.nan
        )
        df["player_id"] = player_id
        df["season"] = datetime.now().year
        df["competition"] = current_comp if current_comp else np.nan
        return df
    
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
    
    # def get_historical_season_stats(self, player_id):

    #     expected_stats = [
    #         'Accurate long balls', 'Accurate long balls %',
    #         'Accurate long balls %_per90', 'Accurate long balls_per90',
    #         'Aerial duels won', 'Aerial duels won %', 'Aerial duels won %_per90',
    #         'Aerial duels won_per90', 'Assists', 'Assists_per90', 'Chances created',
    #         'Chances created_per90','Clean sheets', 'Clean sheets_per90', 'Clearances',
    #         'Clearances_per90','Defensive contributions', 'Defensive contributions_per90',
    #         'Dispossessed', 'Dispossessed_per90', 'Dribbled past',
    #         'Dribbled past_per90', 'Duels won', 'Duels won %', 'Duels won %_per90',
    #         'Duels won_per90', 'Expected assists (xA)',
    #         'Expected assists (xA)_per90', 'Expected goals (xG)',
    #         'Expected goals (xG)_per90', 'Fouls committed', 'Fouls committed_per90',
    #         'Fouls won', 'Fouls won_per90', 'Goals',
    #         'Goals conceded while on pitch', 'Goals conceded while on pitch_per90',
    #         'Goals_per90', 'Interceptions', 'Interceptions_per90',
    #         'Possession won final 3rd', 'Possession won final 3rd_per90',
    #         'Recoveries', 'Recoveries_per90', 'Red cards', 'Red cards_per90',
    #         'Shots', 'Shots on target', 'Shots on target_per90', 'Shots_per90',
    #         'Successful crosses', 'Successful crosses %',
    #         'Successful crosses %_per90', 'Successful crosses_per90',
    #         'Successful dribbles', 'Successful dribbles %',
    #         'Successful dribbles %_per90', 'Successful dribbles_per90',
    #         'Successful passes', 'Successful passes %', 'Successful passes %_per90',
    #         'Successful passes_per90', 'Tackles', 'Tackles_per90', 'Touches',
    #         'Touches in opposition box', 'Touches in opposition box_per90',
    #         'Touches_per90', 'Yellow cards', 'Yellow cards_per90',
    #         'xG against while on pitch', 'xG against while on pitch_per90',
    #         'xG on target (xGOT)', 'xG on target (xGOT)_per90',
    #         'player_id', 'season'
    #     ]

    #     url = self.BASE_URL.format(player_id)
    #     self.driver.get(url)
    #     time.sleep(5)

    #     soup = BeautifulSoup(self.driver.page_source, "lxml")

    #     # ---- build competition list ----
    #     competitions = []
    #     for optgroup in soup.find_all("optgroup"):
    #         season_group = optgroup.get("label", "").strip()

    #         for option in optgroup.find_all("option"):
    #             competitions.append({
    #                 "season_group": season_group,
    #                 "competition": option.text.strip(),
    #                 "value": option.get("value")
    #             })

    #     results = []

    #     for comp in competitions:
    #         try:
    #             print(f"Scraping {comp['season_group']} - {comp['competition']}")

    #             # locate select fresh each loop
    #             select_element = self.driver.find_element(
    #                 By.CSS_SELECTOR,
    #                 "div.css-1odgbvs-SeasonSelectCSS select"
    #             )

    #             dropdown = Select(select_element)

    #             # capture old state (IMPORTANT FIX)
    #             old_first_stat = self.driver.find_element(
    #                 By.CSS_SELECTOR,
    #                 "div.css-15lw8xy-SeasonPerformanceCSS div.css-13fpglj-StatValue"
    #             ).text

    #             # SELECT via Selenium ONLY (do NOT click option manually)
    #             dropdown.select_by_value(comp["value"])

    #             # force change event (important for React)
    #             self.driver.execute_script("""
    #                 arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
    #             """, select_element)

    #             # WAIT for actual stat change (not DOM presence)
    #             WebDriverWait(self.driver, 10).until(
    #                 lambda d: d.find_element(
    #                     By.CSS_SELECTOR,
    #                     "div.css-15lw8xy-SeasonPerformanceCSS div.css-13fpglj-StatValue"
    #                 ).text != old_first_stat
    #             )

    #             time.sleep(1)

    #             soup = BeautifulSoup(self.driver.page_source, "lxml")

    #             stats_box = soup.find(
    #                 "div",
    #                 class_="css-15lw8xy-SeasonPerformanceCSS"
    #             )

    #             if not stats_box:
    #                 print("Skipping (no stats box)")
    #                 continue

    #             rows = []

    #             stat_items = stats_box.find_all(
    #                 "div",
    #                 class_="css-1v73fp6-StatItemCSS e1fqvhy50"
    #             )

    #             for group in stat_items:
    #                 title = group.find("span")
    #                 value = group.find("div")

    #                 if not title:
    #                     continue

    #                 rows.append({
    #                     "stat": title.get_text(strip=True),
    #                     "value": value.get_text(strip=True) if value else np.nan
    #                 })

    #             if not rows:
    #                 continue

    #             df = pd.DataFrame(rows).set_index("stat").T

    #             for stat in expected_stats:
    #                 if stat not in df.columns:
    #                     df[stat] = np.nan

    #             df["player_id"] = player_id
    #             df["season"] = comp["season_group"]
    #             df["competition"] = comp["competition"]

    #             results.append(df)

    #         except Exception as e:
    #             print(f"Skipping {comp['competition']} -> {e}")
    #             continue


    def historical_season_stats(self, player_id):

        url = self.BASE_URL.format(player_id)
        self.driver.get(url)

        select_locator = (By.CSS_SELECTOR, "div[class*='SeasonSelectCSS'] select")
        stats_locator = (By.CSS_SELECTOR, "div[class*='SeasonPerformanceCSS']")

        select_element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(select_locator)
        )

        previous_text = ""

        # get number of options once (safe because we re-fetch element each loop)
        option_count = len(select_element.find_elements(By.TAG_NAME, "option"))

        for index in range(option_count):

            select_element = self.driver.find_element(*select_locator)

            option = select_element.find_elements(By.TAG_NAME, "option")[index]
            option_text = option.text
            print(f"Scraping: {option_text}")

            # 🔥 KEY FIX: force real user-like event triggering
            self.driver.execute_script("""
                const select = arguments[0];
                const value = select.options[arguments[1]].value;

                select.value = value;

                select.dispatchEvent(new Event('input', { bubbles: true }));
                select.dispatchEvent(new Event('change', { bubbles: true }));
            """, select_element, index)

            # Wait for stats to actually change (not just appear)
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.find_element(*stats_locator).text != previous_text
                )
            except Exception:
                print("⚠️ Stats did not update for this selection")
                continue

            stats_container = self.driver.find_element(*stats_locator)
            stats_text = stats_container.text

            previous_text = stats_text

            print(stats_text)
            print("-" * 30)