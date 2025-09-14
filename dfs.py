import requests
import json
from pulp import *
import pandas as pd 
import streamlit as st 

position_bounds = {
    'QB': {'min': 1, 'max': 1},
    'RB': {'min': 2, 'max': 3},
    'WR': {'min': 3,'max': 4},
    'TE': {'min': 1, 'max': 2},
    'DST': {'min': 1, 'max': 1}
} 
teams = {}

def run_app():
    sleeper_players = fetch_sleeper_projections()       
    dk_players = fetch_dk_players(sleeper_players)
    players_df = pd.DataFrame.from_dict(dk_players, orient='index')
    players_df['lock'] = False
    players_df['exclude'] = False
    lineup_df = pd.DataFrame({
        'POS': ['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'FLEX', 'DST'],
        'NAME': ['']*9,
        'TEAM': ['']*9,
        'SAL': ['']*9,
        'PROJ': ['']*9,
    })    
    load_streamlit(dk_players, players_df, lineup_df)

def fetch_sleeper_projections():
    sleeper_API = requests.get('https://api.sleeper.app/projections/nfl/2025/2?season_type=regular&position%5B%5D=DEF&position%5B%5D=K&position%5B%5D=RB&position%5B%5D=QB&position%5B%5D=TE&position%5B%5D=WR&order_by=ppr')
    json_sleeper_data = json.loads(sleeper_API.text)    
    sleeper_players = {}
    for item in json_sleeper_data:
        projection = item['stats'].get('pts_ppr')
        if projection and item['player']['position'] == 'DEF': 
            sleeper_players.update({item['player']['last_name']: projection})
        elif projection: 
            sleeper_players.update({item['player']['first_name'] + ' ' + item['player']['last_name']: projection})
    return sleeper_players

def fetch_dk_players(sleeper_players): 
    dk_API = requests.get('https://api.draftkings.com/draftgroups/v1/draftgroups/133233/draftables')
    json_dk_data = json.loads(dk_API.text)
    dk_players = {}
    for index, item in enumerate(json_dk_data['draftables']):
        if item['draftStatAttributes'][0].get('id') == 90:                
            if index == 0 or item['playerId'] != json_dk_data['draftables'][index - 1]['playerId']:
                parts = item['competition']['name'].split('@')
                opponent = parts[0].strip() if parts[1].strip() == item['teamAbbreviation'] else parts[1].strip() 
                info = {str(index):{'name': item['displayName'], 'position': item['position'], 'team': item['teamAbbreviation'], 'opp': opponent, 'FFPG': item['draftStatAttributes'][0]['value'], 'OPRK': item['draftStatAttributes'][1]['value'], 'salary': item['salary'], 'projection':0}}
                if item['displayName'] in sleeper_players:
                    info[str(index)]['projection'] = sleeper_players[item['displayName']]
                elif len(item['displayName'].split(' ', 2)) > 2:
                    short = ' '.join(item['displayName'].split(' ', 2)[:2])
                    if short in sleeper_players:
                        info[str(index)]['projection'] = sleeper_players[short]
                dk_players.update(info)
            if item['position'] == 'DST' and item['teamAbbreviation'] not in teams:
                teams.update({item['teamAbbreviation']: opponent}) 
    return dk_players

def load_streamlit(dk_players, players_df, lineup_df):
    st.set_page_config(layout='wide')    
    col_a, col_b, col_c = st.columns([1,9,1])
    col_a.empty() 
    col_c.empty()
    with col_b:
        st.markdown('#### Custom Fantasy Optimizer')
        input_controls = display_input_controls()
    st.markdown('')
    col_d, col_e, col_f = st.columns([17,1,12])
    with col_d:
        edited_df, queue_controls = display_players_queue(players_df)
    col_e.empty()
    with col_f: 
        errors = lock_player_errors(edited_df)
        for e in errors: 
            st.error(e)          
        totals_placeholder, lineup_placeholder = display_lineup(lineup_df)
        col_g, col_h, col_i = st.columns([1,2,1])
        col_g.empty()
        col_i.empty()
        with col_h: 
            if st.button('Optimize Lineup', use_container_width=True):
                team_constraints, player_pos_constraints = customize_constraints(input_controls, queue_controls)
                results, rem_sal, total_proj, status = optimize_dk_players(dk_players, team_constraints, player_pos_constraints)
                final_lineup = display_results(results, lineup_df)
                if status != 'Optimal':
                    st.warning('Error: Optimal solution not found.')
                totals_placeholder.write(f'**Proj** {round(total_proj, 2)} | **Rem Salary** ${rem_sal}')
                lineup_placeholder.dataframe(final_lineup, height=352, hide_index=True, column_config={'NAME': st.column_config.Column(width='medium'), 'TEAM': st.column_config.Column(width='small')})

def display_input_controls():
    with st.container():
        col_0, col_1, col_2, col_3, col_4, col_5, col_6 = st.columns([2,1,1,1,1,1,1])
        with col_0: 
            st.markdown('Stacks -- Same Team')   
            st.markdown('Stacks -- Opposing')   
        with col_1:
            qb_rb = st.checkbox('QB/RB', key='RB TEAM')
            qb_rb_opp = st.checkbox('QB/RB', key='RB OPP')
        with col_2:
            qb_wr = st.checkbox('QB/WR', key='WR TEAM')
            qb_wr_opp = st.checkbox('QB/WR', key='WR OPP')
        with col_3:
            qb_te = st.checkbox('QB/TE', key='TE TEAM')
            qb_te_opp = st.checkbox('QB/TE', key='TE OPP')
        with col_4:
            qb_flex= st.checkbox('QB/FLEX')
        with col_5:
            qb_wr_te = st.checkbox('QB/WR or TE')
        with col_6:
            dst_rb = st.checkbox('RB/DST')
        col_7, col_8, col_9, col_10, col_11, col_12 = st.columns([2,1,1,1,1,2])
        with col_7: 
            st.markdown('Exclude Opposing DST')
        with col_8:
            dst_excl = st.toggle('Excl.', label_visibility='collapsed') 
        with col_9:
            st.markdown('Max 1 RB')
        with col_10:
            rb_max = st.toggle('Max,', label_visibility='collapsed')
        with col_11:
            st.markdown('Custom FLEX')  
        with col_12:
            flex_input = st.radio('Flex', ['RB', 'WR', 'TE'], label_visibility='collapsed', index=None, horizontal=True)    
    qb_opp_stacks = {'QB_RB_OPP': qb_rb_opp, 'QB_WR_OPP': qb_wr_opp, 'QB_TE_OPP': qb_te_opp}
    qb_team_stacks = {'QB_RB': qb_rb, 'QB_WR': qb_wr, 'QB_TE': qb_te, 'QB_WR_TE': qb_wr_te, 'QB_RB_WR_TE': qb_flex}
    input_controls = {
        'qb_stacks_team': qb_team_stacks,
        'qb_stacks_opp': qb_opp_stacks,
        'RB_DST': dst_rb,
        'dst_exclude_opp': dst_excl,
        'rb_max': rb_max,
        'flex_req': flex_input
    }
    return input_controls

def display_players_queue(players_df):
    with st.container():
        col_7, col_8 = st.columns(2)
        with col_7:
            st.markdown("##### Players")
        col_8.empty()
        edited_df = st.data_editor(
            players_df,
            height=420,
            hide_index=True,
            column_config={
                "name": st.column_config.Column("NAME", disabled=True),
                "position": st.column_config.Column("POS", disabled=True),
                "team": st.column_config.Column("TEAM", disabled=True),
                "opp": st.column_config.Column("OPP", disabled=True),
                "FFPG": st.column_config.Column("FFPG", disabled=True),
                "OPRK": st.column_config.Column("OPRK", disabled=True),
                "projection": st.column_config.Column("PROJ", disabled=True),
                "salary": st.column_config.Column("SAL", disabled=True),
                "lock": st.column_config.CheckboxColumn("🔐"),
                "exclude": st.column_config.CheckboxColumn("🚫")
            },
            key="player_pool", 
            use_container_width=True
        )
    queue_controls = {
        'include': edited_df[edited_df['lock']].index.tolist(), 
        'exclude': edited_df[edited_df['exclude']].index.tolist()
    }
    return edited_df, queue_controls

def display_lineup(lineup_df):
    with st.container():
        col_9, col_10 = st.columns(2)
        with col_9:
            st.markdown("##### Lineup")
        totals_placeholder = col_10.empty()
        totals_placeholder.write("**Proj** 0.00 | **Rem Salary** $50000")
        lineup_placeholder = st.empty() 
        lineup_placeholder.dataframe(lineup_df, column_config={'NAME': st.column_config.Column(width='medium'), 'TEAM': st.column_config.Column(width='small')}, height=352, hide_index=True, use_container_width=True)
    return totals_placeholder, lineup_placeholder

def lock_player_errors(edited_df):
    errors = []
    edited_df.loc[edited_df["lock"], "exclude"] = False
    if len(edited_df[edited_df["lock"]]) > 9:
        errors.append("❌ You can’t lock more than 9 players.")    
    flex_count = edited_df[edited_df["lock"]]["position"].isin(["RB", "WR", "TE"]).sum()
    if flex_count > 7:
        errors.append("❌ You can’t lock more than 7 FLEX eligible players.")
    for pos, caps in position_bounds.items():
        pos_count = (edited_df[edited_df["lock"]]["position"] == pos).sum()
        if pos_count > caps['max']:
            errors.append(f"❌ You can’t lock more than {caps['max']} {pos}(s).")
    return errors

def customize_constraints(input_controls, queue_controls):    
    team_constraints = {
        'qb_stacks': [],
        'qb_stacks_opposing': [],
        'RB_DST': input_controls['RB_DST'],
        'dst_exclude_opp': input_controls['dst_exclude_opp'],
        'rb_max': input_controls['rb_max']
    }
    player_pos_constraints = dict(queue_controls)
    player_pos_constraints.update({'flex_req': input_controls['flex_req']})
    if input_controls['qb_stacks_team']['QB_RB'] == True:
        team_constraints['qb_stacks'].append('RB')
    if input_controls['qb_stacks_team']['QB_WR'] == True:
        team_constraints['qb_stacks'].append('WR')
    if input_controls['qb_stacks_team']['QB_TE'] == True:
        team_constraints['qb_stacks'].append('TE')
    if input_controls['qb_stacks_team']['QB_RB_WR_TE'] == True:
        team_constraints['qb_stacks'].append('FLEX')
    if input_controls['qb_stacks_team']['QB_WR_TE'] == True:
        team_constraints['qb_stacks'].append('WR_TE')
    for key, value in input_controls['qb_stacks_opp'].items():
        if value:
            abbr = key[3:5]
            team_constraints['qb_stacks_opposing'].append(abbr) 
    return team_constraints, player_pos_constraints

def optimize_dk_players(dk_players, team_constraints, player_pos_constraints):
    prob = LpProblem('Optimize', LpMaximize)
    player_vars = LpVariable.dicts('Select', dk_players.keys(), 0, 1, cat='Binary')
    prob += lpSum(dk_players[p]["salary"] * player_vars[p] for p in dk_players) <= 50000
    prob += lpSum(player_vars[p] for p in dk_players) == 9  
    prob += lpSum(player_vars[p] for p in dk_players if dk_players[p]['position'] in ["RB", "WR", "TE"]) == 7  
    for pos, bound in position_bounds.items():
        prob += lpSum([player_vars[p] for p in dk_players if dk_players[p]['position'] == pos]) <= bound['max']
        prob += lpSum([player_vars[p] for p in dk_players if dk_players[p]['position'] == pos]) >= bound['min']
    if player_pos_constraints['flex_req']:
        prob += lpSum([player_vars[p] for p in dk_players if dk_players[p]['position'] == player_pos_constraints['flex_req']]) == position_bounds[player_pos_constraints['flex_req']]['max']       
    for p in player_pos_constraints['include']:
        player_vars[p].lowBound = 1
    for p in player_pos_constraints['exclude']:
        player_vars[p].upBound = 0
    optimizer_team_constraints(dk_players, player_vars, prob, team_constraints)
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
    return results, rem_sal, total_proj, status

def optimizer_team_constraints(dk_players, player_vars, prob, team_constraints):
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

def display_results(results, lineup_df):
    final_lineup = lineup_df.copy()    
    for player in results:
        row = final_lineup[(final_lineup["POS"] == results[player]['position']) & (final_lineup["NAME"] == "")].index
        if len(row) > 0:
            final_lineup.at[row[0], "NAME"] = results[player]['name'] 
            final_lineup.at[row[0], "TEAM"] = f"{results[player]['team']} - {results[player]['opp']}"
            final_lineup.at[row[0], "PROJ"] = results[player]['projection'] 
            final_lineup.at[row[0], "SAL"] = results[player]['salary']
        else:
            flex_row = final_lineup[(final_lineup["POS"] == "FLEX") & (final_lineup["NAME"] == "")].index
            if len(flex_row) > 0 and results[player]['position'] in ['RB', 'WR', 'TE']:
                final_lineup.at[flex_row[0], "NAME"] = results[player]['name']
                final_lineup.at[flex_row[0], "TEAM"] = f"{results[player]['team']} - {results[player]['opp']}"
                final_lineup.at[flex_row[0], "PROJ"] = results[player]['projection']
                final_lineup.at[flex_row[0], "SAL"] = results[player]['salary']
    return final_lineup

run_app()