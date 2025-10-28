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
    add_custom_player_constraints(dk_players, player_vars, prob, input_controls)
    add_custom_team_constraints(dk_players, teams, player_vars, prob, input_controls)    
    prob += lpSum(dk_players[p]['projection'] * player_vars[p] for p in dk_players)
    prob.solve()
    results = {}
    rem_sal = 50000
    for player in dk_players:
        if player_vars[player].varValue == 1:
            results[player_vars[player]] = dk_players[player]
            rem_sal -= dk_players[player]['salary']
    return(results, rem_sal, pulp.value(prob.objective), LpStatus[prob.status])

def add_custom_player_constraints(dk_players, player_vars, prob, input_controls):
    if input_controls['flex_team']: 
        prob += lpSum(player_vars[p] for p in dk_players if dk_players[p]['team'] == input_controls['flex_team'] and dk_players[p]['position'] in ['RB', 'WR', 'TE']) >= 1  
    if input_controls['flex_req']:
        prob += lpSum([player_vars[p] for p in dk_players if dk_players[p]['position'] == input_controls['flex_req']]) == position_bounds[input_controls['flex_req']]['max']       
    include = st.session_state.players_df[st.session_state.players_df['lock']].index.tolist()
    exclude = st.session_state.players_df[st.session_state.players_df['exclude']].index.tolist()
    for p in include:
        player_vars[p].lowBound = 1
    for p in exclude:
        player_vars[p].upBound = 0

def add_custom_team_constraints(dk_players, teams, player_vars, prob, input_controls):
    for team in teams:         
        if any(input_controls['qb_stacks_team'].values()) or any(input_controls['qb_stacks_opp'].values()):
            add_qb_stack_constraints(dk_players, player_vars, prob, input_controls, teams, team)
        if input_controls['RB_DST'] or input_controls['rb_max'] or input_controls['dst_exclude_opp']: 
            dst = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == "DST"])
            rb = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == 'RB'])  
            if input_controls['RB_DST'] == True:
                prob += lpSum(rb) >= lpSum(dst)
            if input_controls['rb_max'] == True:
                prob += lpSum(rb) <= 1
            if input_controls['dst_exclude_opp'] == True:
                other = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == teams[team] and dk_players[k]['position'] != 'DST'])  
                prob += lpSum(other) <= lpSum((1 - lpSum(dst)) * 9)

def add_qb_stack_constraints(dk_players, player_vars, prob, input_controls, teams, team):
    qb = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == "QB"])
    for pos, value in input_controls['qb_stacks_team'].items():
        if len(pos) > 5 and value:
            pos_arr = pos.split('_')[1:]
            positions = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] in pos_arr])
            prob += lpSum(positions) >= lpSum(qb)
        elif value:
            abbr = pos[3:5]
            position = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == abbr])  
            prob += lpSum(position) >= lpSum(qb)
    for pos_opp, value in input_controls['qb_stacks_opp'].items():
        if value:
            abbr_opp = pos_opp[3:5]
            position_opp = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == teams[team] and dk_players[k]['position'] == abbr_opp])  
            prob += lpSum(position_opp) >= lpSum(qb)