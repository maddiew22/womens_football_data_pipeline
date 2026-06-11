import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mplsoccer import Pitch
from statsbombpy import sb
import re
from matplotlib.lines import Line2D
import unicodedata

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


def plot_pass_map(player, competition_name=None):

    competitions = sb.competitions()

    womens_comps = competitions[
        competitions["competition_gender"] == "female"
    ].copy()

    womens_comps["season_year"] = (
        womens_comps["season_name"].str.extract(r"(\d{4})").astype(int)
    )

    womens_comps_sorted = womens_comps.sort_values(
        by="season_year",
        ascending=False
    )

    if competition_name:
        normalized_comp = competition_name.split("(")[0].strip()

        womens_comps_sorted["base_comp"] = womens_comps_sorted[
            "competition_name"
        ].str.replace(r"\s*\(\d{4}/\d{4}\)\s*", "", regex=True)

        womens_comps_sorted = womens_comps_sorted[
            womens_comps_sorted["base_comp"].str.lower() == normalized_comp.lower()
        ]

        if womens_comps_sorted.empty:
            raise ValueError("Competition not found")

    target_match = None
    target_comp = None
    matched_player_name = None

    for _, comp_row in womens_comps_sorted.iterrows():
        c_id = comp_row["competition_id"]
        s_id = comp_row["season_id"]

        try:
            matches = sb.matches(competition_id=c_id, season_id=s_id)
            matches["match_date"] = pd.to_datetime(matches["match_date"])
            matches_sorted = matches.sort_values(by="match_date", ascending=False)
        except:
            continue

        for _, match_row in matches_sorted.iterrows():
            m_id = match_row["match_id"]

            try:
                lineups = sb.lineups(match_id=m_id)

                found_name = None

                for squad in lineups.values():
                    for pname in squad["player_name"].values:
                        if match_player_name(player, pname):
                            found_name = pname
                            break
                    if found_name:
                        break

                if found_name:
                    matched_player_name = found_name
                    target_match = match_row
                    target_comp = comp_row
                    break

            except:
                continue

        if target_match is not None:
            break

    if target_match is None:
        raise ValueError(f"No matches found for {player}")

    match_id = target_match["match_id"]
    home_team = target_match["home_team"]
    away_team = target_match["away_team"]
    match_date = target_match["match_date"].strftime("%Y-%m-%d")

    events_df = sb.events(match_id=match_id)
    passes_df = events_df[events_df["type"] == "Pass"].copy()

    passes_df["player"] = passes_df["player"].astype(str)

    player_name_for_filter = matched_player_name if matched_player_name else player

    player_passes = passes_df[
        passes_df["player"].str.lower() == player_name_for_filter.lower()
    ].copy()

    passes_received = passes_df[
        passes_df["pass_recipient"].notna()
    ].copy()

    passes_received = passes_received[
        passes_received["pass_recipient"].astype(str).str.lower()
        == player_name_for_filter.lower()
    ].copy()

    player_passes = player_passes.dropna(
        subset=["location", "pass_end_location"]
    ).copy()

    passes_received = passes_received.dropna(
        subset=["location", "pass_end_location"]
    ).copy()

    player_passes["x"] = player_passes["location"].apply(lambda loc: loc[0])
    player_passes["y"] = player_passes["location"].apply(lambda loc: loc[1])
    player_passes["end_x"] = player_passes["pass_end_location"].apply(lambda loc: loc[0])
    player_passes["end_y"] = player_passes["pass_end_location"].apply(lambda loc: loc[1])

    passes_received["x"] = passes_received["location"].apply(lambda loc: loc[0])
    passes_received["y"] = passes_received["location"].apply(lambda loc: loc[1])
    passes_received["end_x"] = passes_received["pass_end_location"].apply(lambda loc: loc[0])
    passes_received["end_y"] = passes_received["pass_end_location"].apply(lambda loc: loc[1])

    successful_passes = player_passes[player_passes["pass_outcome"].isna()].copy()
    unsuccessful_passes = player_passes[player_passes["pass_outcome"].notna()].copy()
    received_completed = passes_received[passes_received["pass_outcome"].isna()].copy()

    fig, ax = plt.subplots(figsize=(16, 11))

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
            width=1.5,
            headwidth=5,
            headlength=5,
            color="#00FFCC",
            ax=ax,
            alpha=0.85,
        )

    if not unsuccessful_passes.empty:
        pitch.arrows(
            unsuccessful_passes["x"],
            unsuccessful_passes["y"],
            unsuccessful_passes["end_x"],
            unsuccessful_passes["end_y"],
            width=1.2,
            headwidth=4,
            headlength=4,
            color="#aa3333",
            ax=ax,
            alpha=0.4,
        )

    if not received_completed.empty:
        pitch.arrows(
            received_completed["x"],
            received_completed["y"],
            received_completed["end_x"],
            received_completed["end_y"],
            width=1.5,
            headwidth=5,
            headlength=5,
            color="#FF00AA",
            ax=ax,
            alpha=0.6,
        )

    legend_elements = []

    if not successful_passes.empty:
        legend_elements.append(Line2D([0], [0], color="#00FFCC", lw=2, label="Completed Passes"))

    if not unsuccessful_passes.empty:
        legend_elements.append(Line2D([0], [0], color="#aa3333", lw=2, label="Incomplete Passes"))

    if not received_completed.empty:
        legend_elements.append(Line2D([0], [0], color="#FF00AA", lw=2, label="Received Passes"))

    if legend_elements:
        ax.legend(
            handles=legend_elements,
            facecolor="#1a1a1a",
            edgecolor="none",
            fontsize=11,
            loc="upper left",
            labelcolor="white",
        )

    ax.scatter(
        successful_passes["x"],
        successful_passes["y"],
        color="#00FFCC",
        s=40,
        edgecolors="white",
        zorder=3,
    )

    ax.set_title(
        f"{player_name_for_filter}\n{home_team} vs {away_team} ({match_date})",
        color="white",
    )

    fig.set_facecolor("#1a1a1a")

    return (
        fig,
        len(successful_passes),
        len(unsuccessful_passes),
        len(received_completed),
    )