import pulp
import pandas as pd

def optimize_team(df, budget=1000):
    """
    Selects optimal 15-man squad, starting XI, and Captain using PuLP.
    """
    players = df['id'].tolist()
    
    # Decision Variables
# Decision Variables
    squad = pulp.LpVariable.dicts("squad", players, lowBound=0, upBound=1, cat='Integer')
    lineup = pulp.LpVariable.dicts("lineup", players, lowBound=0, upBound=1, cat='Integer')
    captain = pulp.LpVariable.dicts("captain", players, lowBound=0, upBound=1, cat='Integer')
    
    # Objective: Maximize (Starting XI xP + Captain xP)
    prob = pulp.LpProblem("FPL_Optimizer", pulp.LpMaximize)
    prob += pulp.lpSum([lineup[i] * df.loc[df['id'] == i, 'custom_xP'].values[0] for i in players] + 
                       [captain[i] * df.loc[df['id'] == i, 'custom_xP'].values[0] for i in players])
    
    # Constraint: Logic linkages
    for i in players:
        prob += lineup[i] <= squad[i]
        prob += captain[i] <= lineup[i]
    
    # Constraint: Budget
    prob += pulp.lpSum([squad[i] * df.loc[df['id'] == i, 'now_cost'].values[0] for i in players]) <= budget
    
    # Constraint: Total Players
    prob += pulp.lpSum([squad[i] for i in players]) == 15
    prob += pulp.lpSum([lineup[i] for i in players]) == 11
    prob += pulp.lpSum([captain[i] for i in players]) == 1
    
    # Constraint: Max 3 players per team
    teams = df['team_name'].unique()
    for t in teams:
        team_players = df[df['team_name'] == t]['id'].tolist()
        prob += pulp.lpSum([squad[i] for i in team_players]) <= 3
        
    # Constraint: Squad Positional Limits
    gks = df[df['position'] == 'GK']['id'].tolist()
    defs = df[df['position'] == 'DEF']['id'].tolist()
    mids = df[df['position'] == 'MID']['id'].tolist()
    fwds = df[df['position'] == 'FWD']['id'].tolist()
    
    prob += pulp.lpSum([squad[i] for i in gks]) == 2
    prob += pulp.lpSum([squad[i] for i in defs]) == 5
    prob += pulp.lpSum([squad[i] for i in mids]) == 5
    prob += pulp.lpSum([squad[i] for i in fwds]) == 3
    
    # Constraint: Starting XI Positional Limits (Valid FPL Formations)
    prob += pulp.lpSum([lineup[i] for i in gks]) == 1
    prob += pulp.lpSum([lineup[i] for i in defs]) >= 3
    prob += pulp.lpSum([lineup[i] for i in mids]) >= 2
    prob += pulp.lpSum([lineup[i] for i in fwds]) >= 1
    
    # Solve
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    
    # Extract results
    squad_ids = [i for i in players if squad[i].varValue == 1]
    lineup_ids = [i for i in players if lineup[i].varValue == 1]
    captain_id = [i for i in players if captain[i].varValue == 1][0]
    
    res_df = df[df['id'].isin(squad_ids)].copy()
    res_df['is_starter'] = res_df['id'].apply(lambda x: 1 if x in lineup_ids else 0)
    res_df['is_captain'] = res_df['id'].apply(lambda x: 1 if x == captain_id else 0)
    
    # Sort for UI presentation
    res_df['pos_order'] = res_df['position'].map({'GK': 1, 'DEF': 2, 'MID': 3, 'FWD': 4})
    res_df = res_df.sort_values(['is_starter', 'pos_order', 'custom_xP'], ascending=[False, True, False])
    
    return res_df, prob.objective.value()
