import pandas as pd
import numpy as np

def calculate_xp(df, risk_differential_weight=0.0):
    """
    Calculates Expected Points (xP) using the 5-Layer Statistical Hierarchy.
    risk_differential_weight: -1.0 (Safe/Chalk) to 1.0 (Differential/Punt)
    """
    df = df.copy()
    
    # -----------------------------------------
    # LAYER 2: Primary Predictors (Weight: 45%)
    # -----------------------------------------
    df['layer2_score'] = (
        (df['expected_goals_per_90'] * 4.0) + 
        (df['expected_assists_per_90'] * 3.0) - 
        (df['expected_goals_conceded_per_90'] * 0.5)
    )
    df.loc[df['position'].isin(['GK', 'DEF']), 'layer2_score'] += 1.5
    
    # -----------------------------------------
    # LAYER 3: Underlying Form & Volume (Weight: 25%)
    # -----------------------------------------
    df['layer3_score'] = df['ict_index'] / 10.0
    
    # -----------------------------------------
    # LAYER 4: Historical Trends & Security (Weight: 20%)
    # -----------------------------------------
    df['layer4_score'] = (df['form'] * 0.5) + (df['ep_next'] * 0.5)
    
    df['set_piece_boost'] = 0.0
    df.loc[df['penalties_order'] == 1, 'set_piece_boost'] += 1.0
    df.loc[df['direct_freekicks_order'] == 1, 'set_piece_boost'] += 0.5
    df.loc[df['corners_and_indirect_freekicks_order'] == 1, 'set_piece_boost'] += 0.3
    
    df['layer4_score'] += df['set_piece_boost']
    
    # -----------------------------------------
    # LAYER 5: Marginal Edge & Tie-Breakers (Weight: 10%)
    # -----------------------------------------
    bps_per_minute = np.where(df['minutes'] > 0, df['bps'] / df['minutes'], 0)
    df['layer5_score'] = bps_per_minute * 90 / 10.0
    
    ownership_factor = (50 - df['selected_by_percent']) / 50.0 
    df['layer5_score'] += (ownership_factor * risk_differential_weight * 2.0)
    
    # -----------------------------------------
    # FINAL xP AGGREGATION
    # -----------------------------------------
    df['custom_xP'] = (
        (df['layer2_score'] * 0.45) +
        (df['layer3_score'] * 0.25) +
        (df['layer4_score'] * 0.20) +
        (df['layer5_score'] * 0.10)
    )
    
    df['custom_xP'] = df['custom_xP'].clip(lower=0.0)
    
    return df