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

def plot_pass_map(player: str, passes_data):
    """
    Plot pass map for a player using data from API endpoint.
    
    Args:
        player: Player name (for title display)
        passes_data: List of dicts or DataFrame with columns: player, pass_recipient, 
                    start_x, start_y, end_x, end_y, pass_outcome
    
    Returns:
        tuple: (fig, successful_passes_count, unsuccessful_passes_count, received_passes_count)
    """
    import pandas as pd
    from matplotlib.lines import Line2D
    from mplsoccer import Pitch
    import matplotlib.pyplot as plt
    
    # Convert to DataFrame if it's a list of dicts
    if isinstance(passes_data, list):
        passes_df = pd.DataFrame(passes_data)
    else:
        passes_df = passes_data.copy()
    
    # Check for data
    if passes_df.empty:
        raise ValueError(f"No pass data found for {player}")
    
    # Convert string columns to float for coordinates
    for col in ['start_x', 'start_y', 'end_x', 'end_y']:
        if col in passes_df.columns:
            passes_df[col] = pd.to_numeric(passes_df[col], errors='coerce')
    
    # Rename columns for consistency
    player_passes = passes_df.rename(columns={
        'start_x': 'x',
        'start_y': 'y',
    }).copy()
    
    # Filter for passes received by this player
    passes_received = passes_df[
        passes_df["pass_recipient"].notna() & (passes_df["pass_recipient"] != "None")
    ].copy()
    passes_received = passes_received[
        passes_received["pass_recipient"].astype(str).str.lower() == player.lower()
    ].rename(columns={
        'start_x': 'x',
        'start_y': 'y',
    })
    
    # Convert coordinates to float for received passes too
    for col in ['x', 'y', 'end_x', 'end_y']:
        if col in passes_received.columns:
            passes_received[col] = pd.to_numeric(passes_received[col], errors='coerce')
    
    # Split by pass outcome
    # In string format from run_query: 'None' or 'nan' = successful, anything else = unsuccessful
    successful_passes = player_passes[
        (player_passes["pass_outcome"].isna()) | 
        (player_passes["pass_outcome"].isin(['None', 'nan', '']))
    ]
    unsuccessful_passes = player_passes[
        (player_passes["pass_outcome"].notna()) & 
        (~player_passes["pass_outcome"].isin(['None', 'nan', '']))
    ]
    received_completed = passes_received[
        (passes_received["pass_outcome"].isna()) | 
        (passes_received["pass_outcome"].isin(['None', 'nan', '']))
    ]
    
    # Create plot
    fig, ax = plt.subplots(figsize=(16, 11))
    pitch = Pitch(
        pitch_type="statsbomb",
        pitch_color="#1a1a1a",
        line_color="#444444",
        linewidth=2,
    )
    pitch.draw(ax=ax)
    
    # Plot successful passes
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
    
    # Plot unsuccessful passes
    if not unsuccessful_passes.empty:
        pitch.arrows(
            unsuccessful_passes["x"],
            unsuccessful_passes["y"],
            unsuccessful_passes["end_x"],
            unsuccessful_passes["end_y"],
            color="#ff009d",
            width=1.5,
            headwidth=5,
            headlength=5,
            alpha=0.85,
            linestyle="--",
            ax=ax,
        )
    
    # Plot received passes
    # if not received_completed.empty:
    #     pitch.arrows(
    #         received_completed["x"],
    #         received_completed["y"],
    #         received_completed["end_x"],
    #         received_completed["end_y"],
    #         color="#2200FF",
    #         width=1.5,
    #         headwidth=5,
    #         headlength=5,
    #         alpha=0.6,
    #         ax=ax,
    #     )
    
    # Create legend
    legend_elements = []
    if not successful_passes.empty:
        legend_elements.append(
            Line2D([0], [0], color="#00FFCC", lw=2, label="Completed Passes")
        )
    if not unsuccessful_passes.empty:
        legend_elements.append(
            Line2D([0], [0], color="#ff009d", lw=2, label="Incomplete Passes")
        )
    if not received_completed.empty:
        legend_elements.append(
            Line2D([0], [0], color="#2200FF", lw=2, label="Received Passes")
        )
    
    if legend_elements:
        ax.legend(
            handles=legend_elements,
            facecolor="#1a1a1a",
            edgecolor="none",
            labelcolor="white",
            loc="upper left"
        )
    
    ax.set_title(f"{player} Pass Map", color="white")
    fig.set_facecolor("#1a1a1a")
    
    return (
        fig,
        len(successful_passes),
        len(unsuccessful_passes),
        len(received_completed),
    )


def plot_heat_map(player: str, events_data):
    """
    Plot heat map for a player using data from API endpoint.
    
    Args:
        player: Player name (for title display)
        events_data: List of dicts or DataFrame with columns: x, y, type, minute, second
    
    Returns:
        tuple: (fig, total_actions, own_half_pct, opp_half_pct)
    """
    import pandas as pd
    from mplsoccer import Pitch
    import matplotlib.pyplot as plt
    
    # Convert to DataFrame if it's a list of dicts
    if isinstance(events_data, list):
        events_df = pd.DataFrame(events_data)
    else:
        events_df = events_data.copy()
    
    # Check for data
    if events_df.empty:
        raise ValueError(f"No event data found for {player}")
    
    # Convert string columns to float for coordinates
    events_df['x'] = pd.to_numeric(events_df['x'], errors='coerce')
    events_df['y'] = pd.to_numeric(events_df['y'], errors='coerce')
    
    # Drop rows with invalid coordinates
    events_df = events_df.dropna(subset=['x', 'y'])
    
    if events_df.empty:
        raise ValueError(f"No valid coordinate data found for {player}")
    
    # Create plot
    fig, ax = plt.subplots(figsize=(16, 11))
    pitch = Pitch(
        pitch_type="statsbomb",
        pitch_color="#1a1a1a",
        line_color="#444444",
        linewidth=2,
    )
    pitch.draw(ax=ax)
    
    # KDE plot for heat map
    pitch.kdeplot(
        events_df["x"],
        events_df["y"],
        fill=True,
        cmap="PuRd",
        levels=100,
        alpha=0.65,
        ax=ax,
    )
    
    # Scatter plot for individual events
    ax.scatter(
        events_df["x"],
        events_df["y"],
        color="white",
        edgecolors="black",
        alpha=0.35,
        s=25,
        zorder=2,
    )
    
    ax.set_title(f"{player} Heat Map", color="white")
    fig.set_facecolor("#1a1a1a")
    
    # Calculate statistics
    total_actions = len(events_df)
    own_half_actions = len(events_df[events_df["x"] < 60])
    opp_half_actions = len(events_df[events_df["x"] >= 60])
    
    return (
        fig,
        total_actions,
        round(own_half_actions / total_actions * 100, 1) if total_actions > 0 else 0,
        round(opp_half_actions / total_actions * 100, 1) if total_actions > 0 else 0,
    )