from datetime import datetime

import psycopg2
import pandas as pd

class PostgresDB:
    def __init__(self, db_url):
        self.db_url = db_url
        self.conn = None
        self.cur = None

    def connect(self):
        """Open database connection"""
        self.conn = psycopg2.connect(self.db_url)
        self.cur = self.conn.cursor()

    def execute(self, query, params=None):
        """Run a single query"""
        self.cur.execute(query, params)

    def executemany(self, query, params_list):
        """Run batch insert/update"""
        self.cur.executemany(query, params_list)

    def fetchall(self):
        """Fetch all results"""
        return self.cur.fetchall()

    def commit(self):
        """Commit transaction"""
        self.conn.commit()

    def close(self):
        """Close connection safely"""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()

       
    @staticmethod
    def safe_int(value):
        if pd.isna(value) or value == "":
            return None

        if isinstance(value, str):
            value = value.replace(",", "")

        return int(float(value))

    @staticmethod
    def safe_float(value):
        if pd.isna(value) or value == "":
            return None

        if isinstance(value, str):
            value = value.replace(",", "")

        return float(value)

    def save_raw_json(self, player_id, json_data):
        createdate = datetime.now()
        insert_query = """
            INSERT INTO fotmob_data.raw_player_overview (player_id, createdate, json_data)
            VALUES (%s, %s, %s)
            ON CONFLICT (player_id)
            DO UPDATE SET createdate = EXCLUDED.createdate,
            DO UPDATE SET json_data = EXCLUDED.json_data
        """
        self.execute(insert_query, (player_id, createdate, json_data))
        self.commit()
    
    def save_player_fotmob_data(self, bio_df, season_overview_df, season_stats_df):
        insert_bio_query = """
            INSERT INTO fotmob_data.player_bio (player_id, name, height, birthdate, country, position, preferred_foot, club)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (player_id)
            DO UPDATE SET
                name = EXCLUDED.name,
                height = EXCLUDED.height,
                birthdate = EXCLUDED.birthdate,
                country = EXCLUDED.country,
                position = EXCLUDED.position,
                preferred_foot = EXCLUDED.preferred_foot,
                club = EXCLUDED.club
        """

        bio_rows = [
            (row["player_id"], row["Name"], row["Height"], None if pd.isna(row["Birthdate"]) else row["Birthdate"], row["Country"], row["Primary Position"], row["Preferred foot"], row["Club"])
            for _, row in bio_df.iterrows()
        ]
        self.executemany(insert_bio_query, bio_rows)
        self.commit()


        insert_season_overview_query = """
            INSERT INTO fotmob_data.season_overview (player_id, season, goals, assists, matches_played, matches_started, minutes_played, fotmob_rating)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (player_id, season)
            DO UPDATE SET
                goals = EXCLUDED.goals,
                assists = EXCLUDED.assists,
                matches_played = EXCLUDED.matches_played,
                matches_started = EXCLUDED.matches_started,
                minutes_played = EXCLUDED.minutes_played,
                fotmob_rating = EXCLUDED.fotmob_rating
        """

        season_overview_rows = [
            (row["player_id"], row["season"], None if pd.isna(row["Goals"]) else row["Goals"], None if pd.isna(row["Assists"]) else row["Assists"], None if pd.isna(row["Matches"]) else row["Matches"], None if pd.isna(row["Started"]) else row["Started"], int(row["Minutes played"].replace(",", "")) if not pd.isna(row["Minutes played"]) else None, row["Rating"])
            for _, row in season_overview_df.iterrows()
        ]

        self.executemany(insert_season_overview_query, season_overview_rows)
        self.commit()

        insert_season_stats_query = """
            INSERT INTO fotmob_data.season_stats (player_id, season, goals, goals_per_90, xg, xg_per_90, xgot, xgot_per_90, shots, shots_per_90, 
                shots_on_target, shots_on_target_per_90, assists, assists_per_90, xa, xa_per_90, successful_passes, successful_passes_per_90, pass_success_rate, pass_success_rate_per_90,
                accurate_long_balls, accurate_long_balls_per_90, long_ball_accuracy, long_ball_accuracy_per_90, chances_created, chances_created_per_90, duels_won, duels_won_per_90,
                percent_duels_won, percent_duels_won_per_90, aerial_duels_won, aerial_duels_won_per_90, percent_aerial_duels_won, percent_aerial_duels_won_per_90, touches, touches_per_90,
                touches_in_opp_box, touches_in_opp_box_per_90, dispossessed, dispossessed_per_90, fouls_won, fouls_won_per_90, defensive_contributions, defensive_contributions_per_90, tackles, 
                tackles_per_90, interceptions, interceptions_per_90, recoveries, recoveries_per_90,clearances, clearances_per_90, clean_sheets, 
                clean_sheets_per_90, goals_conceded_while_on_pitch, xg_against_when_on_pitch, goals_conceded_while_on_pitch_per_90, xg_against_when_on_pitch_per_90,
                yellow_cards, yellow_cards_per_90, red_cards, red_cards_per_90, successful_crosses, successful_crosses_per_90, successful_cross_rate, successful_cross_rate_per_90,
                successful_dribbles, successful_dribbles_per_90, successful_dribble_rate, successful_dribble_rate_per_90, fouls_committed, fouls_committed_per_90, dribbled_past, dribbled_past_per_90, 
                possession_won_in_final_third, possession_won_in_final_third_per_90, competition)
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (player_id, season, competition)
            DO UPDATE SET
                goals = EXCLUDED.goals,
                goals_per_90 = EXCLUDED.goals_per_90,
                xg = EXCLUDED.xg,
                xg_per_90 = EXCLUDED.xg_per_90,
                xgot = EXCLUDED.xgot,
                xgot_per_90 = EXCLUDED.xgot_per_90, 
                shots = EXCLUDED.shots,
                shots_per_90 = EXCLUDED.shots_per_90,
                shots_on_target = EXCLUDED.shots_on_target,
                shots_on_target_per_90 = EXCLUDED.shots_on_target_per_90,
                assists = EXCLUDED.assists,
                assists_per_90 = EXCLUDED.assists_per_90,
                xa = EXCLUDED.xa,
                xa_per_90 = EXCLUDED.xa_per_90,
                successful_passes = EXCLUDED.successful_passes,
                successful_passes_per_90 = EXCLUDED.successful_passes_per_90,
                pass_success_rate = EXCLUDED.pass_success_rate,
                pass_success_rate_per_90 = EXCLUDED.pass_success_rate_per_90,
                accurate_long_balls = EXCLUDED.accurate_long_balls,
                accurate_long_balls_per_90 = EXCLUDED.accurate_long_balls_per_90,
                long_ball_accuracy = EXCLUDED.long_ball_accuracy,   
                long_ball_accuracy_per_90 = EXCLUDED.long_ball_accuracy_per_90,
                chances_created = EXCLUDED.chances_created,
                chances_created_per_90 = EXCLUDED.chances_created_per_90,
                duels_won = EXCLUDED.duels_won,
                duels_won_per_90 = EXCLUDED.duels_won_per_90,
                percent_duels_won = EXCLUDED.percent_duels_won,
                percent_duels_won_per_90 = EXCLUDED.percent_duels_won_per_90,
                aerial_duels_won = EXCLUDED.aerial_duels_won,
                aerial_duels_won_per_90 = EXCLUDED.aerial_duels_won_per_90,
                percent_aerial_duels_won = EXCLUDED.percent_aerial_duels_won,
                percent_aerial_duels_won_per_90 = EXCLUDED.percent_aerial_duels_won_per_90,
                touches = EXCLUDED.touches,
                touches_per_90 = EXCLUDED.touches_per_90,
                touches_in_opp_box = EXCLUDED.touches_in_opp_box,
                touches_in_opp_box_per_90 = EXCLUDED.touches_in_opp_box_per_90,
                dispossessed = EXCLUDED.dispossessed,
                dispossessed_per_90 = EXCLUDED.dispossessed_per_90,
                fouls_won = EXCLUDED.fouls_won,
                fouls_won_per_90 = EXCLUDED.fouls_won_per_90,
                defensive_contributions = EXCLUDED.defensive_contributions,
                defensive_contributions_per_90 = EXCLUDED.defensive_contributions_per_90,   
                tackles = EXCLUDED.tackles,
                tackles_per_90 = EXCLUDED.tackles_per_90,
                interceptions = EXCLUDED.interceptions,
                interceptions_per_90 = EXCLUDED.interceptions_per_90,   
                recoveries = EXCLUDED.recoveries,
                recoveries_per_90 = EXCLUDED.recoveries_per_90,
                clearances = EXCLUDED.clearances,
                clearances_per_90 = EXCLUDED.clearances_per_90,
                clean_sheets = EXCLUDED.clean_sheets,
                clean_sheets_per_90 = EXCLUDED.clean_sheets_per_90,
                goals_conceded_while_on_pitch = EXCLUDED.goals_conceded_while_on_pitch,
                xg_against_when_on_pitch = EXCLUDED.xg_against_when_on_pitch,
                goals_conceded_while_on_pitch_per_90 = EXCLUDED.goals_conceded_while_on_pitch_per_90,
                xg_against_when_on_pitch_per_90 = EXCLUDED.xg_against_when_on_pitch_per_90,
                yellow_cards = EXCLUDED.yellow_cards,
                yellow_cards_per_90 = EXCLUDED.yellow_cards_per_90,
                red_cards = EXCLUDED.red_cards,
                red_cards_per_90 = EXCLUDED.red_cards_per_90,
                successful_crosses = EXCLUDED.successful_crosses,
                successful_crosses_per_90 = EXCLUDED.successful_crosses_per_90,
                successful_cross_rate = EXCLUDED.successful_cross_rate,
                successful_cross_rate_per_90 = EXCLUDED.successful_cross_rate_per_90,
                successful_dribbles = EXCLUDED.successful_dribbles,
                successful_dribbles_per_90 = EXCLUDED.successful_dribbles_per_90,
                successful_dribble_rate = EXCLUDED.successful_dribble_rate,
                successful_dribble_rate_per_90 = EXCLUDED.successful_dribble_rate_per_90,
                fouls_committed = EXCLUDED.fouls_committed,
                fouls_committed_per_90 = EXCLUDED.fouls_committed_per_90,
                dribbled_past = EXCLUDED.dribbled_past,
                dribbled_past_per_90 = EXCLUDED.dribbled_past_per_90,
                possession_won_in_final_third = EXCLUDED.possession_won_in_final_third,
                possession_won_in_final_third_per_90 = EXCLUDED.possession_won_in_final_third_per_90
        """

        # season_stats_rows = [
        #     (self.safe_int(row["player_id"]), self.safe_int(row["season"]), self.safe_int(row["Goals"]), self.safe_float(row["Goals_per90"]), self.safe_float(row["Expected goals (xG)"]), self.safe_float(row["Expected goals (xG)_per90"]), self.safe_float(row["xG on target (xGOT)"]), self.safe_float(row["xG on target (xGOT)_per90"]), 
        #      self.safe_int(row["Shots"].replace(",", "")), self.safe_float(row["Shots_per90"]), self.safe_int(row["Shots on target"]), self.safe_float(row["Shots on target_per90"]), self.safe_int(row["Assists"]), self.safe_float(row["Assists_per90"]), self.safe_float(row["Expected assists (xA)"]), self.safe_float(row["Expected assists (xA)_per90"]), self.safe_int(row["Successful passes"].replace(",", "")), self.safe_float(row["Successful passes_per90"]), 
        #      self.safe_float(row["Successful passes %"]), self.safe_float(row["Successful passes %_per90"]), self.safe_int(row["Accurate long balls"].replace(",", "")), self.safe_float(row["Accurate long balls_per90"]), self.safe_float(row["Accurate long balls %"]), self.safe_float(row["Accurate long balls %_per90"]), self.safe_int(row["Chances created"]), self.safe_float(row["Chances created_per90"]), 
        #      self.safe_int(row["Duels won"].replace(",", "")), self.safe_float(row["Duels won_per90"]), self.safe_float(row["Duels won %"]), self.safe_float(row["Duels won %_per90"]), self.safe_int(row["Aerial duels won"].replace(",", "")), self.safe_float(row["Aerial duels won_per90"]), self.safe_float(row["Aerial duels won %"]), self.safe_float(row["Aerial duels won %_per90"]), self.safe_int(row["Touches"].replace(",", "")), self.safe_float(row["Touches_per90"]),
        #      self.safe_int(row["Touches in opposition box"].replace(",", "")), self.safe_float(row["Touches in opposition box_per90"]), self.safe_int(row["Dispossessed"].replace(",", "")), self.safe_float(row["Dispossessed_per90"]), self.safe_int(row["Fouls won"]), self.safe_float(row["Fouls won_per90"]), self.safe_int(row["Defensive contributions"]), self.safe_float(row["Defensive contributions_per90"]), self.safe_int(row["Tackles"].replace(",", "")),
        #      self.safe_float(row["Tackles_per90"]), self.safe_int(row["Interceptions"].replace(",", "")), self.safe_float(row["Interceptions_per90"]), self.safe_int(row["Recoveries"].replace(",", "")), self.safe_float(row["Recoveries_per90"]), self.safe_int(row["Clearances"].replace(",", "")), self.safe_float(row["Clearances_per90"]), self.safe_int(row["Clean sheets"]), self.safe_float(row["Clean sheets_per90"]),
        #      self.safe_int(row["Goals conceded while on pitch"]), self.safe_float(row["xG against while on pitch"]), self.safe_float(row["Goals conceded while on pitch_per90"]), self.safe_float(row["xG against while on pitch_per90"]), self.safe_int(row["Yellow cards"]), self.safe_float(row["Yellow cards_per90"]), self.safe_int(row["Red cards"]), self.safe_float(row["Red cards_per90"]), self.safe_int(row["Successful crosses"]), self.safe_float(row["Successful crosses_per90"]), self.safe_float(row["Successful crosses %"]), self.safe_float(row["Successful crosses %_per90"]),
        #      self.safe_float(row["Successful dribbles"]), self.safe_float(row["Successful dribbles_per90"]), self.safe_float(row["Successful dribbles %"]), self.safe_float(row["Successful dribbles %_per90"]), self.safe_int(row["Fouls committed"]), self.safe_float(row["Fouls committed_per90"]), self.safe_int(row["Dribbled past"]), self.safe_float(row["Dribbled past_per90"]), self.safe_int(row["Possession won final 3rd"]), self.safe_float(row["Possession won final 3rd_per90"]), row["competition"])
        #     for _, row in season_stats_df.iterrows()
        # ]
  
        # self.executemany(insert_season_stats_query, season_stats_rows)
        # self.commit()
 
