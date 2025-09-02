import requests
import json
from pulp import *
import streamlit as st 
import pandas as pd 

pos_numbers = {
    'QB': {'min': 1, 'max': 1},
    'RB': {'min': 2, 'max': 3},
    'WR': {'min': 3, 'max': 4},
    'TE': {'min': 1, 'max': 2},
    'DST': {'min': 1, 'max': 1}
} 

def start_app():
    # Fetch Sleeper projections and DraftKings contest players.
    sleeper_players = fetch_sleeper_projections()       
    dk_players = fetch_dk_players(sleeper_players)
    # Load Streamlit interface.
    st.set_page_config(layout="wide")    
    col_a, col_b = st.columns([5, 4])
    with col_a:
        st.header("Custom Fantasy Optimizer")
    # Display custom inputs, player queue, and lineup table. 
    with col_b:
        qb_rb, qb_wr, qb_te, dst_rb, dst_input, flex_input = display_custom_inputs()
    col_c, col_d = st.columns([4, 3]) 
    with col_c:
        edited_df = display_player_queue(dk_players)       
    with col_d:
        # Error if locked players exceed maximums. 
        errors = lock_player_errors(edited_df)
        for e in errors: 
            st.error(e)
        totals_placeholder, lineup_placeholder, lineup_df = display_lineup_table()
        # Run optimizer and display results. 
        col_e, col_f, col_g = st.columns([1, 2, 1]) 
        with col_f:
            if st.button("Optimize Lineup", use_container_width=True):
                constraints = constraint_vars(edited_df, flex_input, qb_rb, qb_wr, qb_te, dst_rb, dst_input)
                results, rem_sal, total_proj, status = optimize_dk_players(dk_players, constraints)
                final_lineup = display_results(results, lineup_df)
                if status != "Optimal":
                    st.warning("Error: Optimal solution not found.")
                totals_placeholder.write(f"**Projection:** {round(total_proj, 2)} | **Rem. Salary:** ${rem_sal:05}")
                lineup_placeholder.dataframe(final_lineup, height=352, hide_index=True, column_config={"Name": st.column_config.Column(width="medium")}, use_container_width=True)

def fetch_sleeper_projections():
    # Fetch projections from sleeper API.
    sleeper_API = requests.get('https://api.sleeper.app/projections/nfl/2023/18?season_type=regular&position%5B%5D=DEF&position%5B%5D=K&position%5B%5D=RB&position%5B%5D=QB&position%5B%5D=TE&position%5B%5D=WR&order_by=ppr')
    json_sleeper_data = json.loads(sleeper_API.text)    
    # Create dictionary of names and projections. 
    sleeper_players = {}
    for item in json_sleeper_data:
        projection = item['stats'].get('pts_ppr')
        if projection and item['player']['position'] == 'DEF': 
            sleeper_players.update({item['player']['last_name']: projection})
        elif projection: 
            sleeper_players.update({item['player']['first_name'] + ' ' + item['player']['last_name']: projection})
    return sleeper_players

def fetch_dk_players(sleeper_players): 
    # Fetch contest data from DraftKings API. 
    dk_API = requests.get('https://api.draftkings.com/draftgroups/v1/draftgroups/131064/draftables')
    json_dk_data = json.loads(dk_API.text)
    dk_players = {}
    # Loop through players and skip duplicates. 
    for index, item in enumerate(json_dk_data['draftables']):
        if item['draftStatAttributes'][0].get('id') == 90:                
            if index == 0 or item['playerId'] != json_dk_data['draftables'][index - 1]['playerId']:
                parts = item['competition']['name'].split('@')
                opp = parts[0].strip() if parts[1].strip() == item['teamAbbreviation'] else parts[1].strip() 
                # Match sleeper projection to player.
                if item['displayName'] in sleeper_players:
                    dk_players.update({str(index): {'name': item['displayName'], 'position': item['position'], 'team': item['teamAbbreviation'], 'opp': opp, 'FFPG': item['draftStatAttributes'][0]['value'], 'projection': sleeper_players[item['displayName']], 'salary': item['salary']}})
                elif item['displayName'][:15] in sleeper_players:
                    dk_players.update({str(index): {'name': item['displayName'], 'position': item['position'], 'team': item['teamAbbreviation'], 'opp': opp, 'FFPG': item['draftStatAttributes'][0]['value'], 'projection': sleeper_players[item['displayName'][:15]], 'salary': item['salary']}})
    return dk_players

def display_custom_inputs():
    with st.container(height=110):
        st.write("**Customizations**")
        col_1, col_2, col_3, col_4, col_5 = st.columns([2, 3, 3, 3, 4])
        with col_1:
            st.caption('Stacks')  
        with col_2:
            qb_rb = st.checkbox('QB/RB')
        with col_3:
            qb_wr = st.checkbox('QB/WR')
        with col_4:
            qb_te = st.checkbox('QB/TE')
        with col_5:
            dst_rb = st.checkbox('RB/DST')
        col_8, col_9 = st.columns([3, 5])
        with col_8:
            st.caption("Exclude teams opposing Defense")
            st.caption('FLEX Requirement')  
        with col_9:
            dst_input = st.toggle('Exclude', label_visibility='collapsed')   
            flex_input = st.radio('', ['RB', 'WR', 'TE'],  label_visibility="collapsed", index=None, horizontal=True)
    return qb_rb, qb_wr, qb_te, dst_rb, dst_input, flex_input

def display_player_queue(dk_players):
    col_10, col_11, col_12 = st.columns([6,2,1])
    with col_10:
        st.markdown("#### Player Pool")
    with col_11:
        filter_players = st.selectbox('', ['All Players', 'QB', 'RB', 'WR', 'TE', 'DST', 'FLEX'], label_visibility='collapsed')
    if "players_df" not in st.session_state:
        st.session_state.players_df = pd.DataFrame.from_dict(dk_players, orient="index")
        st.session_state.players_df["Lock"] = False
        st.session_state.players_df["Exclude"] = False
    if filter_players == 'All Players':
        view_players = st.session_state.players_df
    elif filter_players == 'FLEX':
        view_players = st.session_state.players_df[st.session_state.players_df["position"].isin(['RB', 'WR', 'TE'])]
    else: 
        view_players = st.session_state.players_df[st.session_state.players_df["position"] == filter_players]
    edited_df = st.data_editor(
        view_players,
        height=420,
        hide_index=True,
        column_config={
            "name": st.column_config.Column("Name", disabled=True),
            "position": st.column_config.Column("Pos.", disabled=True),
            "team": st.column_config.Column("Team", disabled=True),
            "opp": st.column_config.Column("Opp.", disabled=True),
            "FFPG": st.column_config.Column("FFPG", disabled=True),
            "projection": st.column_config.Column("Proj.", disabled=True),
            "salary": st.column_config.Column("Sal.", disabled=True),
            "Lock": st.column_config.CheckboxColumn("Lock"),
            "Exclude": st.column_config.CheckboxColumn("Excl.")
        },
        key="player_pool"
    )
    st.session_state.players_df.update(edited_df)
    return st.session_state.players_df

def lock_player_errors(edited_df):
    errors = []
    edited_df.loc[edited_df["Lock"], "Exclude"] = False
    if len(edited_df[edited_df["Lock"]]) > 9:
        errors.append("❌ You can’t lock more than 9 players.")    
    flex_count = edited_df[edited_df["Lock"]]["position"].isin(["RB", "WR", "TE"]).sum()
    if flex_count > 7:
        errors.append("❌ You can’t lock more than 7 FLEX eligible players.")
    for pos, caps in pos_numbers.items():
        pos_count = (edited_df[edited_df["Lock"]]["position"] == pos).sum()
        if pos_count > caps['max']:
            errors.append(f"❌ You can’t lock more than {caps['max']} {pos}(s).")
    return errors

def display_lineup_table():
    col_6, col_7 = st.columns([6, 10]) 
    with col_6:
        st.markdown("#### Lineup")
    with col_7:    
        st.write("")
        totals_placeholder = st.empty()
        totals_placeholder.write("**Projection:** 00.000 | **Rem. Salary:** $50000")
    lineup_df = pd.DataFrame({
        "Pos.": ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "DST"],
        "Name": [""]*9,
        "Team": [""]*9,
        "Opp.":[""]*9,
        "Proj.": [""]*9,
        "Salary": [""]*9,
    })
    lineup_placeholder = st.empty() 
    lineup_placeholder.dataframe(lineup_df, height=352, hide_index=True, column_config={"Name": st.column_config.Column(width="medium")}, use_container_width=True)
    return totals_placeholder, lineup_placeholder, lineup_df

def constraint_vars(edited_df, flex_input, qb_rb, qb_wr, qb_te, dst_rb, dst_input):
    constraints = {
        'include': edited_df[edited_df["Lock"]].index.tolist(),
        'exclude': edited_df[edited_df["Exclude"]].index.tolist(),
        'flex_req': flex_input,
        'qb_stacks': [],
        'rb_dst': dst_rb,
        'dst_exclude': dst_input
    }
    if qb_rb == True:
        constraints['qb_stacks'].append('RB')
    if qb_wr == True:
        constraints['qb_stacks'].append('WR')
    if qb_te == True:
        constraints['qb_stacks'].append('TE')
    return constraints

def optimize_dk_players(dk_players, constraints):
    # Define PuLP problem and variable. 
    prob = LpProblem('Optimize', LpMaximize)
    player_vars = LpVariable.dicts('Select', dk_players.keys(), 0, 1, cat='Binary')
    # Define PuLP constraints for maximum salary and players per position. 
    prob += lpSum(dk_players[p]["salary"] * player_vars[p] for p in dk_players) <= 50000
    prob += lpSum(player_vars[p] for p in dk_players) == 9  
    prob += lpSum(player_vars[p] for p in dk_players if dk_players[p]['position'] in ["RB", "WR", "TE"]) == 7  
    for pos, numbers in pos_numbers.items():
        prob += lpSum([player_vars[p] for p in dk_players if dk_players[p]['position'] == pos]) <= numbers['max']
        prob += lpSum([player_vars[p] for p in dk_players if dk_players[p]['position'] == pos]) >= numbers['min']
        # Require position for flex if specified and update PuLP constraints for players per flex position.
        if constraints['flex_req'] in ["RB", "WR", "TE"] and constraints['flex_req'] == pos:
            prob += lpSum([player_vars[p] for p in dk_players if dk_players[p]['position'] == constraints['flex_req']]) == numbers['max']       
    # Require inclusion or exclusion of players if specified.
    for p in constraints['include']:
        if p in player_vars:
            player_vars[p].lowBound = 1
    for p in constraints['exclude']:
        if p in player_vars:
            player_vars[p].upBound = 0
    # Define PuLP constraints for maximum players per team.  
    team_constraints(dk_players, player_vars, prob, constraints)
    # Define PuLP objective to maximize total projection and solve. 
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

def team_constraints(dk_players, player_vars, prob, constraints):
    teams = {}
    for data in dk_players.values():
        if data["position"] == 'DST':
            teams.update({data['team']: 0}) 
    for team in teams: 
        # Require QB + RB, WR, and/or TE from the same team if specified.
        for pos in constraints['qb_stacks']:
            flex = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == pos])  
            qb = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == "QB"])
            prob += lpSum(flex) >= lpSum(qb)
        # Require DST + RB from the same team if specified. 
        dst = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == "DST"])
        if constraints['rb_dst'] == True:
            rb = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == 'RB'])  
            prob += lpSum(rb) >= lpSum(dst)
        # Require exclusion of teams opposing DST if specified.  
        if constraints['dst_exclude'] == True:
            other = lpSum([player_vars[k] for k in dk_players if dk_players[k]['opp'] == team and dk_players[k]['position'] != 'DST'])  
            prob += lpSum(other) <= lpSum((1 - lpSum(dst)) * 9)

def display_results(results, lineup_df):
    final_lineup = lineup_df.copy()    
    for player in results:
        row = final_lineup[(final_lineup["Pos."] == results[player]['position']) & (final_lineup["Name"] == "")].index
        if len(row) > 0:
            final_lineup.at[row[0], "Name"] = results[player]['name'] 
            final_lineup.at[row[0], "Team"] = results[player]['team'] 
            final_lineup.at[row[0], "Opp."] = results[player]['opp'] 
            final_lineup.at[row[0], "Proj."] = results[player]['projection'] 
            final_lineup.at[row[0], "Salary"] = results[player]['salary']
        else:
            flex_row = final_lineup[(final_lineup["Pos."] == "FLEX") & (final_lineup["Name"] == "")].index
            if len(flex_row) > 0 and results[player]['position'] in ['RB', 'WR', 'TE']:
                final_lineup.at[flex_row[0], "Name"] = results[player]['name']
                final_lineup.at[flex_row[0], "Team"] = results[player]['team']
                final_lineup.at[flex_row[0], "Opp."] = results[player]['opp'] 
                final_lineup.at[flex_row[0], "Proj."] = results[player]['projection']
                final_lineup.at[flex_row[0], "Salary"] = results[player]['salary']
    return final_lineup

start_app()