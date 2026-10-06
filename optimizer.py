import pandas as pd
import pulp


def optimize_team(df, budget=1000):
    """Selects optimal 15-man squad, starting XI, and Captain using PuLP."""
    players = df['id'].tolist()

    # Pre-build lookup dictionaries for fast performance
    xp_dict = dict(zip(df['id'], df['custom_xP']))
    cost_dict = dict(zip(df['id'], df['now_cost']))

    # Decision Variables: Strict positional arguments (name, lowBound, upBound, cat)
    squad = {
        i: pulp.LpVariable(f"squad_{i}", 0, 1, pulp.LpBinary) for i in players
    }
    lineup = {
        i: pulp.LpVariable(f"lineup_{i}", 0, 1, pulp.LpBinary) for i in players
    }
    captain = {
        i: pulp.LpVariable(f"captain_{i}", 0, 1, pulp.LpBinary) for i in players
    }

    # Objective: Maximize (Starting XI xP + Captain xP)
    prob = pulp.LpProblem("FPL_Optimizer", pulp.LpMaximize)
    prob += pulp.lpSum(
        [lineup[i] * xp_dict[i] for i in players]
        + [captain[i] * xp_dict[i] for i in players]
    )

    # Constraint: Logic linkages
    for i in players:
        prob += lineup[i] <= squad[i]
        prob += captain[i] <= lineup[i]

    # Constraint: Budget
    prob += pulp.lpSum([squad[i] * cost_dict[i] for i in players]) <= budget

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

    # Constraint: Starting XI Positional Limits
    prob += pulp.lpSum([lineup[i] for i in gks]) == 1
    prob += pulp.lpSum([lineup[i] for i in defs]) >= 3
    prob += pulp.lpSum([lineup[i] for i in mids]) >= 2
    prob += pulp.lpSum([lineup[i] for i in fwds]) >= 1

    # Solve
    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    # Extract results safely (> 0.5 handles floating-point precision from solver)
    squad_ids = [
        i
        for i in players
        if squad[i].varValue is not None and squad[i].varValue > 0.5
    ]
    lineup_ids = [
        i
        for i in players
        if lineup[i].varValue is not None and lineup[i].varValue > 0.5
    ]
    captain_ids = [
        i
        for i in players
        if captain[i].varValue is not None and captain[i].varValue > 0.5
    ]
    captain_id = captain_ids[0] if captain_ids else None

    res_df = df[df['id'].isin(squad_ids)].copy()
    res_df['is_starter'] = res_df['id'].apply(
        lambda x: 1 if x in lineup_ids else 0
    )
    res_df['is_captain'] = res_df['id'].apply(
        lambda x: 1 if x == captain_id else 0
    )

    # Sort for UI presentation
    res_df['pos_order'] = res_df['position'].map(
        {'GK': 1, 'DEF': 2, 'MID': 3, 'FWD': 4}
    )
    res_df = res_df.sort_values(
        ['is_starter', 'pos_order', 'custom_xP'], ascending=[False, True, False]
    )

    return res_df, prob.objective.value()
