from pulp import *
import streamlit as st 

position_bounds = {
    'QB': {'min': 1, 'max': 1},
    'RB': {'min': 2, 'max': 3},
    'WR': {'min': 3,'max': 4},
    'TE': {'min': 1, 'max': 2},
    'DST': {'min': 1, 'max': 1}
} 

def optimize_dk_players(dk_players, teams, input_controls):
    prob = LpProblem('Optimize', LpMaximize)
    player_vars = LpVariable.dicts('Select', dk_players.keys(), 0, 1, cat='Binary')
    prob += lpSum(dk_players[p]['salary'] * player_vars[p] for p in dk_players) <= 50000
    prob += lpSum(player_vars[p] for p in dk_players) == 9  
    prob += lpSum(player_vars[p] for p in dk_players if dk_players[p]['position'] in ['RB', 'WR', 'TE']) == 7  
    for pos, bound in position_bounds.items():
        prob += lpSum([player_vars[p] for p in dk_players if dk_players[p]['position'] == pos]) <= bound['max']
        prob += lpSum([player_vars[p] for p in dk_players if dk_players[p]['position'] == pos]) >= bound['min']
    optimize_custom_player_constraints(dk_players, player_vars, prob, input_controls)
    team_constraints = customize_constraint_vars(input_controls)
    optimize_custom_team_constraints(dk_players, teams, player_vars, prob, team_constraints)
    prob += lpSum(dk_players[p]["projection"] * player_vars[p] for p in dk_players)
    prob.solve()
    results = {}
    rem_sal = 50000
    for player in dk_players:
        if player_vars[player].varValue == 1:
            results[player_vars[player]] = dk_players[player]
            rem_sal -= dk_players[player]['salary']
    total_proj = pulp.value(prob.objective)  
    status = LpStatus[prob.status]
    return(results, rem_sal, total_proj, status)

def optimize_custom_player_constraints(dk_players, player_vars, prob, input_controls):
    if input_controls['flex_req']:
        prob += lpSum([player_vars[p] for p in dk_players if dk_players[p]['position'] == input_controls['flex_req']]) == position_bounds[input_controls['flex_req']]['max']       
    include = st.session_state.players_df[st.session_state.players_df['lock']].index.tolist()
    exclude = st.session_state.players_df[st.session_state.players_df['exclude']].index.tolist()
    for p in include:
        player_vars[p].lowBound = 1
    for p in exclude:
        player_vars[p].upBound = 0

def customize_constraint_vars(input_controls):    
    team_constraints = {
        'qb_stacks': [],
        'qb_stacks_opposing': [],
        'RB_DST': input_controls['RB_DST'],
        'dst_exclude_opp': input_controls['dst_exclude_opp'],
        'rb_max': input_controls['rb_max'],
        'flex_team': input_controls['flex_team']
    }        
    for key, value in input_controls['qb_stacks_team'].items():
        if key == 'QB_WR_TE' and value:
            team_constraints['qb_stacks'].append('WR_TE') 
        elif key == 'QB_RB_WR_TE' and value:
            team_constraints['qb_stacks'].append('FLEX') 
        elif value:
            abbr = key[3:5]
            team_constraints['qb_stacks'].append(abbr) 
    for key, value in input_controls['qb_stacks_opp'].items():
        if value:
            abbr = key[3:5]
            team_constraints['qb_stacks_opposing'].append(abbr) 
    return(team_constraints)

def optimize_custom_team_constraints(dk_players, teams, player_vars, prob, team_constraints):
    if team_constraints['flex_team']: 
        prob += lpSum(player_vars[p] for p in dk_players if dk_players[p]['team'] == team_constraints['flex_team'] and dk_players[p]['position'] in ["RB", "WR", "TE"]) >= 1  
    for team in teams:         
        qb = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == "QB"])
        for pos in team_constraints['qb_stacks']:
            if pos == 'WR_TE':
                wr_te = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] in ["WR", "TE"]])  
                prob += lpSum(wr_te) >= lpSum(qb)
            elif pos == 'FLEX':
                flex = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] in ["RB", "WR", "TE"]])  
                prob += lpSum(flex) >= lpSum(qb)
            else:
                position = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == pos])  
                prob += lpSum(position) >= lpSum(qb)
        for pos_opp in team_constraints['qb_stacks_opposing']:
            position_opp = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == teams[team] and dk_players[k]['position'] == pos_opp])  
            prob += lpSum(position_opp) >= lpSum(qb)
        dst = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == "DST"])
        rb = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == 'RB'])  
        if team_constraints['RB_DST'] == True:
            prob += lpSum(rb) >= lpSum(dst)
        if team_constraints['rb_max'] == True:
            prob += lpSum(rb) <= 1
        if team_constraints['dst_exclude_opp'] == True:
            other = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == teams[team] and dk_players[k]['position'] != 'DST'])  
            prob += lpSum(other) <= lpSum((1 - lpSum(dst)) * 9)