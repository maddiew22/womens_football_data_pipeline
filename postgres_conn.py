import psycopg2


class PostgresDB:
    def __init__(self, host="localhost", database="womens_football_data",
                 user="maddie", password="postgres", port=5432):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        self.conn = None
        self.cur = None

    def connect(self):
        """Open database connection"""
        self.conn = psycopg2.connect(
            host=self.host,
            database=self.database,
            user=self.user,
            password=self.password,
            port=self.port
        )
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

    def save_player_fotmob_data(self, bio_df, season_overview_df, season_stats_df):
        insert_bio_query = """
            INSERT INTO fotmob_data.player_bio (player_id, name, height, birthdate, country, position, preferred_foot)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (player_id)
            DO UPDATE SET
                name = EXCLUDED.name,
                height = EXCLUDED.height,
                birthdate = EXCLUDED.birthdate,
                country = EXCLUDED.country,
                position = EXCLUDED.position,
                preferred_foot = EXCLUDED.preferred_foot
        """

        bio_rows = [
            (row["player_id"], row["Name"], row["Height"], row["Birthdate"], row["Country"], row["Primary Position"], row["Preferred foot"])
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
            (row["player_id"], row["season"], row["Goals"], row["Assists"], row["Matches"], row["Started"], row["Minutes played"], row["Rating"])
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
                tackles_per_90, interceptions, interceptions_per_90, blocked_shots, blocked_shots_per_90, recoveries, recoveries_per_90,clearances, clearances_per_90, clean_sheets, 
                clean_sheets_per_90, goals_conceded_while_on_pitch, xg_against_when_on_pitch, goals_conceded_while_on_pitch_per_90, xg_against_when_on_pitch_per_90,
                yellow_cards, yellow_cards_per_90, red_cards, red_cards_per_90)
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            ON CONFLICT (player_id, season)
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
                blocked_shots = EXCLUDED.blocked_shots,
                blocked_shots_per_90 = EXCLUDED.blocked_shots_per_90,
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
                red_cards_per_90 = EXCLUDED.red_cards_per_90
        """

        season_stats_rows = [
            (int(row["player_id"]), int(row["season"]), int(row["Goals"]), float(row["Goals_per90"]), float(row["Expected goals (xG)"]), float(row["Expected goals (xG)_per90"]), float(row["xG on target (xGOT)"]), float(row["xG on target (xGOT)_per90"]), 
             int(row["Shots"]), float(row["Shots_per90"]), int(row["Shots on target"]), float(row["Shots on target_per90"]), int(row["Assists"]), float(row["Assists_per90"]), float(row["Expected assists (xA)"]), float(row["Expected assists (xA)_per90"]), int(row["Successful passes"]), float(row["Successful passes_per90"]), 
             float(row["Successful passes %"]), float(row["Successful passes %_per90"]), int(row["Accurate long balls"]), float(row["Accurate long balls_per90"]), float(row["Accurate long balls %"]), float(row["Accurate long balls %_per90"]), int(row["Chances created"]), float(row["Chances created_per90"]), 
             int(row["Duels won"]), float(row["Duels won_per90"]), float(row["Duels won %"]), float(row["Duels won %_per90"]), int(row["Aerial duels won"]), float(row["Aerial duels won_per90"]), float(row["Aerial duels won %"]), float(row["Aerial duels won %_per90"]), int(row["Touches"]), float(row["Touches_per90"]),
             int(row["Touches in opposition box"]), float(row["Touches in opposition box_per90"]), int(row["Dispossessed"]), float(row["Dispossessed_per90"]), int(row["Fouls won"]), float(row["Fouls won_per90"]), int(row["Defensive contributions"]), float(row["Defensive contributions_per90"]), int(row["Tackles"]),
             float(row["Tackles_per90"]), int(row["Interceptions"]), float(row["Interceptions_per90"]), int(row["Blocked shots"]), float(row["Blocked shots_per90"]), int(row["Recoveries"]), float(row["Recoveries_per90"]), int(row["Clearances"]), float(row["Clearances_per90"]), int(row["Clean sheets"]), float(row["Clean sheets_per90"]),
             row["Goals conceded while on pitch"], row["xG against while on pitch"], row["Goals conceded while on pitch_per90"], row["xG against while on pitch_per90"], row["Yellow cards"], row["Yellow cards_per90"], row["Red cards"], row["Red cards_per90"])
            for _, row in season_stats_df.iterrows()
        ]

        self.executemany(insert_season_stats_query, season_stats_rows)
        self.commit()

