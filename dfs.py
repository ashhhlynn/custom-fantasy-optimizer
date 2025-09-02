import requests
import json
from pulp import *
import streamlit as st 
import pandas as pd 

def fetch_dk_players(): 
    # Fetch contest data from DraftKings API. 
    dk_API = requests.get('https://api.draftkings.com/draftgroups/v1/draftgroups/131064/draftables')
    json_dk_data = json.loads(dk_API.text)
    sleeper_players = fetch_sleeper_projections()       
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
    display_streamlit(dk_players)

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

def display_streamlit(dk_players):
    st.set_page_config(layout="wide")    
    col_0, col_00 = st.columns([4, 6])
    with col_0: 
        st.header("Custom Fantasy Optimizer")
    with col_00: 
        with st.container(height=140):
            col_1, col_2, col_3 = st.columns([1, 2, 4])
            with col_1:
                st.write('Stacks')
                qb_rb = st.checkbox('QB/RB')
                qb_wr = st.checkbox('QB/WR')
            with col_2:
                st.write('')
                st.write('')
                qb_te = st.checkbox('QB/TE')
                dst_stack_1_select = st.checkbox('RB/DST')
            with col_3:
                flex_input = st.radio('Require FLEX', ['RB', 'WR', 'TE'], index=None, horizontal=True)
                dst_stack_2_select = st.toggle('Exclude Opposing DST')                      
    dst_stack_input = [dst_stack_1_select, dst_stack_2_select]
    col1, col2 = st.columns([5, 4]) 
    # Display player queue
    with col1:
        st.subheader("Player Pool")
        # Option to require inclusion or exclusion of specific players.    
        incl_input, excl_input = display_player_queue(dk_players)      
    # Display lineup table.  
    with col2:
        totals_placeholder, lineup_placeholder, lineup_df = display_lineup_table()
        # Run optimizer and display results. 
        if st.button("Optimize Lineup"):
            qb_stack_input = []
            if qb_rb == True:
                qb_stack_input.append('RB')
            if qb_wr == True:
                qb_stack_input.append('WR')
            if qb_te == True:
                qb_stack_input.append('TE')
            player_vars, rem_sal, total_proj = optimize_dk_players(dk_players, flex_input, incl_input, excl_input, qb_stack_input, dst_stack_input)
            totals_placeholder.write(f"**Total Projection:** {round(total_proj, 2)} | **Remaining Salary:** ${rem_sal}")
            final_lineup = display_results(dk_players, player_vars, lineup_df)
            lineup_placeholder.dataframe(final_lineup, height=352, hide_index=True, column_config={"Name": st.column_config.Column(width="medium")}, use_container_width=True)
                
def display_player_queue(dk_players):
    players_df = pd.DataFrame.from_dict(dk_players, orient="index")
    players_df["Lock"] = False
    players_df["Exclude"] = False
    edited_df = st.data_editor(
        players_df,
        height=540,
        hide_index=True,
        column_config={
            "name": st.column_config.Column("Name", disabled=True),
            "position": st.column_config.Column("Pos.", disabled=True),
            "team": st.column_config.Column("Team", disabled=True),
            "opp": st.column_config.Column("Opp.", disabled=True),
            "FFPG": st.column_config.Column("FFPG", disabled=True),
            "projection": st.column_config.Column("Proj.", disabled=True),
            "salary": st.column_config.Column("Salary", disabled=True),
            "Lock": st.column_config.CheckboxColumn("Lock"),
            "Exclude": st.column_config.CheckboxColumn("Excl.")
        },
        key="player_pool"
    )
    incl_input = edited_df[edited_df["Lock"]].index.tolist()
    excl_input = edited_df[edited_df["Exclude"]].index.tolist()
    return(incl_input, excl_input)

def display_lineup_table():
    col3, col4 = st.columns([3, 7]) 
    with col3:
        st.subheader("Lineup")
    with col4:    
        st.write("")
        totals_placeholder = st.empty()
        totals_placeholder.write("**Total Projection:** 0.00 | **Remaining Salary:** $50000")
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

def optimize_dk_players(dk_players, flex_input, incl_input, excl_input, qb_stack_input, dst_stack_input):
    # Define PuLP problem and variable. 
    prob = LpProblem('Optimize', LpMaximize)
    player_vars = LpVariable.dicts('Select', dk_players.keys(), 0, 1, cat='Binary')
    # Define PuLP constraints for maximum salary and players per position. 
    pos_numbers = {
        'QB': {'min': 1, 'max': 1},
        'RB': {'min': 2, 'max': 3},
        'WR': {'min': 3, 'max': 4},
        'TE': {'min': 1, 'max': 2},
        'DST': {'min': 1, 'max': 1}
    }        
    prob += lpSum(dk_players[p]["salary"] * player_vars[p] for p in dk_players) <= 50000
    prob += lpSum(player_vars[p] for p in dk_players) == 9  
    prob += lpSum(player_vars[p] for p in dk_players if dk_players[p]['position'] in ["RB", "WR", "TE"]) == 7  
    for pos, numbers in pos_numbers.items():
        prob += lpSum([player_vars[p] for p in dk_players if dk_players[p]['position'] == pos]) <= numbers['max']
        prob += lpSum([player_vars[p] for p in dk_players if dk_players[p]['position'] == pos]) >= numbers['min']
        # Require position for flex if specified and update PuLP constraints for players per flex position.
        if flex_input in ["RB", "WR", "TE"] and flex_input == pos:
            prob += lpSum([player_vars[p] for p in dk_players if dk_players[p]['position'] == flex_input]) == numbers['max']       
    # Require inclusion or exclusion of players if specified.
    for p in incl_input:
        if p in player_vars:
            player_vars[p].lowBound = 1
    for p in excl_input:
        if p in player_vars:
            player_vars[p].upBound = 0
    # Define PuLP constraints for maximum players per team.  
    team_constraints(dk_players, player_vars, prob, qb_stack_input, dst_stack_input)
    # Define PuLP objective to maximize total projection and solve. 
    prob += lpSum(dk_players[p]["projection"] * player_vars[p] for p in dk_players)
    prob.solve()
    rem_sal = 50000 - sum(dk_players[p]["salary"] * player_vars[p].varValue for p in dk_players)
    total_proj = pulp.value(prob.objective)  
    return(player_vars, rem_sal, total_proj)

def team_constraints(dk_players, player_vars, prob, qb_stack_input, dst_stack_input):
    teams = {}
    for data in dk_players.values():
        if data["position"] == 'DST':
            teams.update({data['team']: 0}) 
    for team in teams: 
        # Require QB + RB, WR, and/or TE from the same team if specified.
        for pos in qb_stack_input:
            flex = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == pos])  
            qb = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == "QB"])
            prob += lpSum(flex) >= lpSum(qb)
        # Require DST + RB from the same team if specified. 
        dst = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == "DST"])
        if dst_stack_input[0] == True:
            rb = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == 'RB'])  
            prob += lpSum(rb) >= lpSum(dst)
        # Require exclusion of teams opposing DST if specified.  
        if dst_stack_input[1] == True:
            other = lpSum([player_vars[k] for k in dk_players if dk_players[k]['opp'] == team and dk_players[k]['position'] != 'DST'])  
            if lpSum(dst) >= 1:
                prob += lpSum(lpSum(other)) == 0
    
def display_results(dk_players, player_vars, lineup_df):
    final_lineup = lineup_df.copy()    
    for player in dk_players:
        if player_vars[player].varValue == 1:
            pos = dk_players[player]['position']
            row = final_lineup[(final_lineup["Pos."] == pos) & (final_lineup["Name"] == "")].index
            if len(row) > 0:
                final_lineup.at[row[0], "Name"] = dk_players[player]['name'] 
                final_lineup.at[row[0], "Team"] = dk_players[player]['team'] 
                final_lineup.at[row[0], "Opp."] = dk_players[player]['opp'] 
                final_lineup.at[row[0], "Proj."] = dk_players[player]['projection'] 
                final_lineup.at[row[0], "Salary"] = dk_players[player]['salary']
            else:
                flex_row = final_lineup[(final_lineup["Pos."] == "FLEX") & (final_lineup["Name"] == "")].index
                if len(flex_row) > 0 and pos in ['RB', 'WR', 'TE']:
                    final_lineup.at[flex_row[0], "Name"] = dk_players[player]['name']
                    final_lineup.at[flex_row[0], "Team"] = dk_players[player]['team']
                    final_lineup.at[flex_row[0], "Opp."] = dk_players[player]['opp'] 
                    final_lineup.at[flex_row[0], "Proj."] = dk_players[player]['projection']
                    final_lineup.at[flex_row[0], "Salary"] = dk_players[player]['salary']
    return(final_lineup)

fetch_dk_players()