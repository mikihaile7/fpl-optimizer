import requests
import pandas as pd
import numpy as np

FPL_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"

def fetch_data():
    """Fetches FPL bootstrap-static data."""
    response = requests.get(FPL_URL)
    response.raise_for_status()
    return response.json()

def process_and_filter_data(data):
    """
    Transforms API JSON into a Pandas DataFrame and applies 
    Layer 1 Hard Constraints (Zero-Tolerance Pre-Filter).
    """
    df_elements = pd.DataFrame(data['elements'])
    df_teams = pd.DataFrame(data['teams'])
    
    # Map Team Name and FDR (Fixture Difficulty Rating next match approximation)
    team_map = df_teams.set_index('id')['name'].to_dict()
    df_elements['team_name'] = df_elements['team'].map(team_map)
    
    # Positional Mapping
    pos_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
    df_elements['position'] = df_elements['element_type'].map(pos_map)
    
    # -----------------------------------------
    # LAYER 1: HARD CONSTRAINTS
    # -----------------------------------------
    # 1. Status: Only active players ('a' = available)
    df_elements = df_elements[df_elements['status'] == 'a']
    
    # 2. Minutes: Must have played > 60 mins total (or high chance of playing)
    df_elements['chance_of_playing_next_round'] = df_elements['chance_of_playing_next_round'].fillna(100).astype(int)
    df_elements = df_elements[df_elements['chance_of_playing_next_round'] == 100]
    
    # Convert numerical strings to floats for downstream calculation
    numeric_cols = [
        'ep_next', 'form', 'expected_goals_per_90', 'expected_assists_per_90',
        'expected_goal_involvements_per_90', 'expected_goals_conceded_per_90',
        'ict_index', 'bps', 'selected_by_percent', 'minutes'
    ]
    for col in numeric_cols:
        if col in df_elements.columns:
            df_elements[col] = pd.to_numeric(df_elements[col], errors='coerce').fillna(0)

    return df_elements

def get_min_budget(df):
    """
    Calculates the absolute minimum budget required to form a valid 
    15-player squad (2 GK, 5 DEF, 5 MID, 3 FWD) based on available active players.
    Returns the value in millions (e.g., 64.0).
    """
    min_gk = df[df['position'] == 'GK']['now_cost'].nsmallest(2).sum()
    min_def = df[df['position'] == 'DEF']['now_cost'].nsmallest(5).sum()
    min_mid = df[df['position'] == 'MID']['now_cost'].nsmallest(5).sum()
    min_fwd = df[df['position'] == 'FWD']['now_cost'].nsmallest(3).sum()
    
    total_min_cost = min_gk + min_def + min_mid + min_fwd
    return float(total_min_cost) / 10.0