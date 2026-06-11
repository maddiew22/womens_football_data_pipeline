import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mplsoccer import Pitch
from statsbombpy import sb
import re
from matplotlib.lines import Line2D
import unicodedata
import seaborn as sns

def get_womens_base_competitions():
    competitions = sb.competitions()
    womens_comps = competitions[
        competitions["competition_gender"] == "female"
    ].copy()

    if womens_comps.empty:
        return []

    womens_comps["base_comp"] = womens_comps["competition_name"].str.replace(
        r"\s*\(\d{4}/\d{4}\)\s*", "", regex=True
    )

    return sorted(womens_comps["base_comp"].unique().tolist())


def get_available_players(competition_name):
    competitions = sb.competitions()

    womens_comps = competitions[
        competitions["competition_gender"] == "female"
    ].copy()

    if womens_comps.empty:
        raise ValueError("No women's competitions found via the StatsBomb API.")

    womens_comps["base_comp"] = womens_comps["competition_name"].str.replace(
        r"\s*\(\d{4}/\d{4}\)\s*", "", regex=True
    )

    matching_comps = womens_comps[
        womens_comps["base_comp"].str.lower() == competition_name.lower()
    ].sort_values("season_year", ascending=False)

    if matching_comps.empty:
        raise ValueError(f"Competition '{competition_name}' not found")

    all_players = set()

    for _, comp_row in matching_comps.iterrows():
        try:
            matches = sb.matches(
                competition_id=comp_row["competition_id"],
                season_id=comp_row["season_id"]
            )

            for _, match in matches.iterrows():
                try:
                    lineups = sb.lineups(match_id=match["match_id"])
                    for squad in lineups.values():
                        all_players.update(squad["player_name"].tolist())
                except:
                    pass
        except:
            pass

    return sorted(list(all_players))


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = str(text).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text

def match_player_name(query: str, full_name: str) -> bool:
    if not query or not full_name:
        return False
    q_norm = normalize_text(query)
    f_norm = normalize_text(full_name)
    q_tokens = re.findall(r"\w+", q_norm)
    return all(tok in f_norm for tok in q_tokens)

def get_player_matches(player, competition_name=None):
    competitions = sb.competitions()

    womens_comps = competitions[
        competitions["competition_gender"] == "female"
    ].copy()

    womens_comps["season_year"] = (
        womens_comps["season_name"]
        .str.extract(r"(\d{4})")
        .astype(int)
    )

    womens_comps = womens_comps.sort_values(
        "season_year",
        ascending=False
    )

    if competition_name:

        womens_comps["base_comp"] = (
            womens_comps["competition_name"]
            .str.replace(
                r"\s*\(\d{4}/\d{4}\)\s*",
                "",
                regex=True
            )
        )
        womens_comps = womens_comps[
            womens_comps["base_comp"].str.lower()
            == competition_name.lower()
        ]

    player_matches = []

    for _, comp_row in womens_comps.iterrows():

        try:
            matches = sb.matches(
                competition_id=comp_row["competition_id"],
                season_id=comp_row["season_id"]
            )

            matches["match_date"] = pd.to_datetime(
                matches["match_date"]
            )

            matches = matches.sort_values(
                "match_date",
                ascending=False
            )

        except Exception:
            continue

        for _, match in matches.iterrows():

            try:
                lineups = sb.lineups(
                    match_id=match["match_id"]
                )

                found_name = None

                for squad in lineups.values():

                    for pname in squad["player_name"].values:

                        if match_player_name(
                            player,
                            pname
                        ):
                            found_name = pname
                            break

                    if found_name:
                        break

                if found_name:

                    player_matches.append(
                        {
                            "match_id": match["match_id"],
                            "player_name": found_name,
                            "label":
                                f"{match['match_date'].strftime('%Y-%m-%d')} | "
                                f"{match['home_team']} vs "
                                f"{match['away_team']}"
                        }
                    )

            except Exception:
                continue

    return player_matches

def plot_pass_map(player, match_id):

    events_df = sb.events(match_id=match_id)

    passes_df = events_df[
        events_df["type"] == "Pass"
    ].copy()

    passes_df["player"] = (
        passes_df["player"]
        .astype(str)
    )

    player_passes = passes_df[
        passes_df["player"].str.lower()
        == player.lower()
    ].copy()

    passes_received = passes_df[
        passes_df["pass_recipient"].notna()
    ].copy()

    passes_received = passes_received[
        passes_received["pass_recipient"]
        .astype(str)
        .str.lower()
        == player.lower()
    ].copy()

    player_passes = player_passes.dropna(
        subset=["location", "pass_end_location"]
    )

    passes_received = passes_received.dropna(
        subset=["location", "pass_end_location"]
    )

    if player_passes.empty:
        raise ValueError(
            f"No pass data found for {player}"
        )

    player_passes["x"] = (
        player_passes["location"]
        .apply(lambda x: x[0])
    )
    player_passes["y"] = (
        player_passes["location"]
        .apply(lambda x: x[1])
    )

    player_passes["end_x"] = (
        player_passes["pass_end_location"]
        .apply(lambda x: x[0])
    )
    player_passes["end_y"] = (
        player_passes["pass_end_location"]
        .apply(lambda x: x[1])
    )

    passes_received["x"] = (
        passes_received["location"]
        .apply(lambda x: x[0])
    )
    passes_received["y"] = (
        passes_received["location"]
        .apply(lambda x: x[1])
    )

    passes_received["end_x"] = (
        passes_received["pass_end_location"]
        .apply(lambda x: x[0])
    )
    passes_received["end_y"] = (
        passes_received["pass_end_location"]
        .apply(lambda x: x[1])
    )

    successful_passes = player_passes[
        player_passes["pass_outcome"].isna()
    ]

    unsuccessful_passes = player_passes[
        player_passes["pass_outcome"].notna()
    ]

    received_completed = passes_received[
        passes_received["pass_outcome"].isna()
    ]

    fig, ax = plt.subplots(
        figsize=(16, 11)
    )

    pitch = Pitch(
        pitch_type="statsbomb",
        pitch_color="#1a1a1a",
        line_color="#444444",
        linewidth=2,
    )

    pitch.draw(ax=ax)

    if not successful_passes.empty:
        pitch.arrows(
            successful_passes["x"],
            successful_passes["y"],
            successful_passes["end_x"],
            successful_passes["end_y"],
            color="#00FFCC",
            width=1.5,
            headwidth=5,
            headlength=5,
            alpha=0.85,
            ax=ax,
        )

    if not unsuccessful_passes.empty:
        pitch.arrows(
            unsuccessful_passes["x"],
            unsuccessful_passes["y"],
            unsuccessful_passes["end_x"],
            unsuccessful_passes["end_y"],
            color="#aa3333",
            width=1.2,
            headwidth=4,
            headlength=4,
            alpha=0.4,
            ax=ax,
        )

    if not received_completed.empty:
        pitch.arrows(
            received_completed["x"],
            received_completed["y"],
            received_completed["end_x"],
            received_completed["end_y"],
            color="#FF00AA",
            width=1.5,
            headwidth=5,
            headlength=5,
            alpha=0.6,
            ax=ax,
        )

    legend_elements = []

    if not successful_passes.empty:
        legend_elements.append(
            Line2D(
                [0],
                [0],
                color="#00FFCC",
                lw=2,
                label="Completed Passes"
            )
        )

    if not unsuccessful_passes.empty:
        legend_elements.append(
            Line2D(
                [0],
                [0],
                color="#aa3333",
                lw=2,
                label="Incomplete Passes"
            )
        )

    if not received_completed.empty:
        legend_elements.append(
            Line2D(
                [0],
                [0],
                color="#FF00AA",
                lw=2,
                label="Received Passes"
            )
        )

    if legend_elements:
        ax.legend(
            handles=legend_elements,
            facecolor="#1a1a1a",
            edgecolor="none",
            labelcolor="white",
            loc="upper left"
        )

    ax.set_title(
        f"{player} Pass Map",
        color="white"
    )

    fig.set_facecolor("#1a1a1a")

    return (
        fig,
        len(successful_passes),
        len(unsuccessful_passes),
        len(received_completed),
    )

def plot_heat_map(player, match_id):

    events_df = sb.events(
        match_id=match_id
    )

    events_df["player"] = (
        events_df["player"]
        .astype(str)
    )

    player_events = events_df[
        events_df["player"].str.lower()
        == player.lower()
    ].copy()

    player_events = player_events.dropna(
        subset=["location"]
    )

    if player_events.empty:
        raise ValueError(
            f"No event data found for {player}"
        )

    player_events["x"] = (
        player_events["location"]
        .apply(lambda x: x[0])
    )

    player_events["y"] = (
        player_events["location"]
        .apply(lambda x: x[1])
    )

    fig, ax = plt.subplots(
        figsize=(16, 11)
    )

    pitch = Pitch(
        pitch_type="statsbomb",
        pitch_color="#1a1a1a",
        line_color="#444444",
        linewidth=2,
    )

    pitch.draw(ax=ax)

    pitch.kdeplot(
        player_events["x"],
        player_events["y"],
        fill=True,
        cmap="PuRd",
        levels=100,
        alpha=0.65,
        ax=ax,
    )

    ax.scatter(
        player_events["x"],
        player_events["y"],
        color="white",
        edgecolors="black",
        alpha=0.35,
        s=25,
        zorder=2,
    )

    ax.set_title(
        f"{player} Heat Map",
        color="white"
    )

    fig.set_facecolor("#1a1a1a")

    total_actions = len(player_events)

    own_half_actions = len(
        player_events[
            player_events["x"] < 60
        ]
    )

    opp_half_actions = len(
        player_events[
            player_events["x"] >= 60
        ]
    )

    return (
        fig,
        total_actions,
        round(
            own_half_actions / total_actions * 100,
            1
        ),
        round(
            opp_half_actions / total_actions * 100,
            1
        ),
    )
