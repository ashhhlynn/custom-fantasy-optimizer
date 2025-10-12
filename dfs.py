import requests
import json
from pulp import *
import pandas as pd 
import streamlit as st 
from streamlit_searchbox import st_searchbox

position_bounds = {
    'QB': {'min': 1, 'max': 1},
    'RB': {'min': 2, 'max': 3},
    'WR': {'min': 3,'max': 4},
    'TE': {'min': 1, 'max': 2},
    'DST': {'min': 1, 'max': 1}
} 
teams = {}
games = {}
logos = {
    "ARI": "https://a.espncdn.com/i/teamlogos/nfl/500/ari.png",
    "ATL": "https://a.espncdn.com/i/teamlogos/nfl/500/atl.png",
    "BAL": "https://a.espncdn.com/i/teamlogos/nfl/500/bal.png",
    "BUF": "https://a.espncdn.com/i/teamlogos/nfl/500/buf.png",
    "CAR": "https://a.espncdn.com/i/teamlogos/nfl/500/car.png",
    "CHI": "https://a.espncdn.com/i/teamlogos/nfl/500/chi.png",
    "CIN": "https://a.espncdn.com/i/teamlogos/nfl/500/cin.png",
    "CLE": "https://a.espncdn.com/i/teamlogos/nfl/500/cle.png",
    "DAL": "https://a.espncdn.com/i/teamlogos/nfl/500/dal.png",
    "DEN": "https://a.espncdn.com/i/teamlogos/nfl/500/den.png",
    "DET": "https://a.espncdn.com/i/teamlogos/nfl/500/det.png",
    "GB": "https://a.espncdn.com/i/teamlogos/nfl/500/gb.png",
    "HOU": "https://a.espncdn.com/i/teamlogos/nfl/500/hou.png",
    "IND": "https://a.espncdn.com/i/teamlogos/nfl/500/ind.png",
    "JAX": "https://a.espncdn.com/i/teamlogos/nfl/500/jax.png",
    "KC": "https://a.espncdn.com/i/teamlogos/nfl/500/kc.png",
    "LV": "https://a.espncdn.com/i/teamlogos/nfl/500/lv.png",
    "LAC": "https://a.espncdn.com/i/teamlogos/nfl/500/lac.png",
    "LAR": "https://a.espncdn.com/i/teamlogos/nfl/500/lar.png",
    "MIA": "https://a.espncdn.com/i/teamlogos/nfl/500/mia.png",
    "MIN": "https://a.espncdn.com/i/teamlogos/nfl/500/min.png",
    "NE": "https://a.espncdn.com/i/teamlogos/nfl/500/ne.png",
    "NO": "https://a.espncdn.com/i/teamlogos/nfl/500/no.png",
    "NYG": "https://a.espncdn.com/i/teamlogos/nfl/500/nyg.png",
    "NYJ": "https://a.espncdn.com/i/teamlogos/nfl/500/nyj.png",
    "PHI": "https://a.espncdn.com/i/teamlogos/nfl/500/phi.png",
    "PIT": "https://a.espncdn.com/i/teamlogos/nfl/500/pit.png",
    "SEA": "https://a.espncdn.com/i/teamlogos/nfl/500/sea.png",
    "SF": "https://a.espncdn.com/i/teamlogos/nfl/500/sf.png",
    "TB": "https://a.espncdn.com/i/teamlogos/nfl/500/tb.png",
    "TEN": "https://a.espncdn.com/i/teamlogos/nfl/500/ten.png",
    "WAS": "https://a.espncdn.com/i/teamlogos/nfl/500/wsh.png",
}

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
    sleeper_API = requests.get('https://api.sleeper.app/projections/nfl/2025/6?season_type=regular&position%5B%5D=DEF&position%5B%5D=K&position%5B%5D=RB&position%5B%5D=QB&position%5B%5D=TE&position%5B%5D=WR&order_by=ppr')
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
    dk_API = requests.get('https://api.draftkings.com/draftgroups/v1/draftgroups/135005/draftables')
    json_dk_data = json.loads(dk_API.text)
    dk_players = {}
    for index, item in enumerate(json_dk_data['draftables']):
        if item['draftStatAttributes'][0].get('id') == 90 and (index == 0 or item['playerId'] != json_dk_data['draftables'][index - 1]['playerId']):
            parts = item['competition']['name'].split('@')
            opponent = parts[0].strip() if parts[1].strip() == item['teamAbbreviation'] else parts[1].strip() 
            info = {str(index): {
                'name': item['displayName'],
                'position': item['position'], 
                'team': item['teamAbbreviation'], 
                'opp': opponent, 
                'FFPG': item['draftStatAttributes'][0]['value'], 
                'OPRK': item['draftStatAttributes'][1]['value'], 
                'salary': item['salary'], 
                'projection':0
            }}
            if item['displayName'] in sleeper_players:
                info[str(index)]['projection'] = sleeper_players[item['displayName']]
            elif len(item['displayName'].split(' ', 2)) > 2:
                short = ' '.join(item['displayName'].split(' ', 2)[:2])
                if short in sleeper_players:
                    info[str(index)]['projection'] = sleeper_players[short]
            dk_players.update(info)
        if item['position'] == 'DST' and item['teamAbbreviation'] not in teams:
            teams.update({item['teamAbbreviation']: opponent}) 
            if opponent not in games:
                games.update({item['teamAbbreviation']: opponent})
    return dk_players

def load_streamlit(dk_players, players_df, lineup_df):
    st.set_page_config(layout='wide')           
    # Temp Hidden:  
    # col_1, col_2, col_3 = st.columns([1,6,1])
    # col_1.empty() 
    # with col_2:            
    #    display_game_buttons()
    # col_3.empty()
    # Temp Hidden:
    display_game_button_logos()
    st.markdown(' ')
    st.markdown(' ')
    col_a, col_b, col_c = st.columns([24,2,12])
    with col_a:
        col_a1, col_a2, col_a3 = st.columns([3,1,2])
        with col_a1:
            def search_data(searchterm: str) -> list:
                if not searchterm:
                    return []
                results = players_df[players_df['name'].str.contains(searchterm, case=False)]
                return(results['name'].tolist())            
            selected_value = st_searchbox(search_data, placeholder="Search", key="search_key")
        col_a2.empty()
        with col_a3:
            position_filter = st.selectbox('Filters', ("All", "QB", "RB", "WR", "TE", "DST"), label_visibility='collapsed')    
        edited_df = display_players_queue(players_df, position_filter, selected_value)
    col_b.empty()
    with col_c:
        input_controls = display_input_controls()
        lock_player_errors()
        lineup_placeholder = display_lineup(lineup_df)
        col_g, col_h, col_i, col_j = st.columns([6,3,5,3], vertical_alignment='center')
        col_h.empty()
        col_i.write(f"**Projection**  \n**Rem. Salary**")
        if col_g.button('Optimize', use_container_width=True, type="primary"):
            team_constraints, player_pos_constraints = customize_constraints(input_controls, edited_df)
            results, rem_sal, total_proj, status = optimize_dk_players(dk_players, team_constraints, player_pos_constraints)
            final_lineup = display_results(results, lineup_df)
            if status != 'Optimal':
                st.warning('Error: Optimal solution not found.')
            lineup_placeholder.dataframe(final_lineup, height=352, column_config={'NAME': st.column_config.Column(width=134)}, hide_index=True, use_container_width=True)
            with col_j:
                st.write(round(total_proj, 1), "  \n", rem_sal)
        else:
            with col_j:
                st.write(0.00, "  \n", 50000)

def display_input_controls():
    with st.container(border=True):
        col_c1, col_c2 = st.columns([10,1])
        col_c1.write("**Customize**")
        col_c2.write('⚙️')
        with st.expander("Team Stacks"):
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                qb_rb = st.checkbox('QB + RB')
                qb_wr = st.checkbox('QB + WR')
                qb_te = st.checkbox('QB + TE')
            with col_s2:     
                qb_wr_te = st.checkbox('QB + WR/TE')
                qb_flex = st.checkbox('QB + FLEX')
                dst_rb = st.checkbox('RB + DST')
        with st.expander("Opponent Stacks"):
            qb_rb_opp = st.checkbox('QB + Opp. RB')
            qb_wr_opp = st.checkbox('QB + Opp. WR')
            qb_te_opp = st.checkbox('QB + Opp. TE')
        col_f1, col_f2 = st.columns([32,20], vertical_alignment='bottom')
        options = ["RB", "WR", "TE"]
        with col_f1:
            flex_input = st.segmented_control("FLEX Position and Team (Min 1)", options, selection_mode="single")
        with col_f2:
            flex_team_input = st.selectbox("Flex Team", (teams.keys()), placeholder="Team", label_visibility='collapsed', index=None)        
        dst_excl = st.toggle("Exclude Opposing DST")
        rb_max = st.toggle("Maximum 1 RB / Team")
        input_controls = {
            'qb_stacks_team': {'QB_RB': qb_rb, 'QB_WR': qb_wr, 'QB_TE': qb_te, 'QB_WR_TE': qb_wr_te, 'QB_RB_WR_TE': qb_flex},
            'qb_stacks_opp': {'QB_RB_OPP': qb_rb_opp, 'QB_WR_OPP': qb_wr_opp, 'QB_TE_OPP': qb_te_opp},
            'RB_DST': dst_rb,
            'dst_exclude_opp': dst_excl,
            'rb_max': rb_max,
            'flex_req': flex_input,
            'flex_team': flex_team_input
        }
    return(input_controls)

def display_game_buttons():
    half = math.ceil(len(games)/2)
    cols = st.columns(half)
    if 'selected_game' not in st.session_state:
        st.session_state.selected_game = 'All Games'  
    for i, (t, o) in enumerate(games.items()):
        if len(t) == 3:
            t_ab = t
        else:
            t_ab = t + '&nbsp;&nbsp;'
        if len(o) == 3:
            o_ab = o
        else:
            o_ab = o + '&nbsp;&nbsp;'
        if st.session_state.selected_game == [t, o]:            
            if cols[i % half].button(f"**:primary[●] {t_ab}  \n:primary[●] {o_ab}**", use_container_width=True):
                st.session_state.selected_game = 'All Games'
        else:
            if cols[i % half].button(f"**:primary[●] {t_ab}  \n:primary[●] {o_ab}**", use_container_width=True):
                st.session_state.selected_game = [t, o]            

def display_game_button_logos():
    half = math.ceil(len(games)/2)
    cols = st.columns(half+2) 
    if 'selected_game' not in st.session_state:
        st.session_state.selected_game = 'All Games'  
    for i, (t, o) in enumerate(games.items()):
        with cols[i % half+1]:
            with st.container(border=True, gap=None):
                col_cb1, col_cb2 = st.columns([1,1], vertical_alignment='center')
                with col_cb1:
                    st.image(logos[t], width=20)
                    st.image(logos[o], width=20)
                if col_cb2.button(f'**:primary[{t}  \n{o}]**', type="tertiary"):
                    if st.session_state.selected_game == [t, o]:            
                        st.session_state.selected_game = 'All Games'
                    else: 
                        st.session_state.selected_game = [t, o]  

def display_players_queue(players_df, position_filter, selected_value):
    if 'players_df' not in st.session_state:
        st.session_state.players_df = players_df
    def sync_edits():
        edited_data = st.session_state.data_editor_key['edited_rows']
        for index, updates in edited_data.items():
            original_index = st.session_state.edited_df.iloc[index].name
            st.session_state.players_df.loc[original_index, updates.keys()] = updates.values()   
    if position_filter != 'All' or st.session_state.selected_game != 'All Games':
        if position_filter != 'All':
            filtered_df = st.session_state.players_df[st.session_state.players_df['position'] == position_filter].copy()
        else:
            filtered_df = st.session_state.players_df[st.session_state.players_df['team'].isin(st.session_state.selected_game)].copy()
    else:
        filtered_df = st.session_state.players_df.copy()
    if selected_value:
        filtered_df = st.session_state.players_df[st.session_state.players_df['name'] == selected_value].copy() 
    with st.container():
        st.session_state.edited_df = st.data_editor(
        filtered_df,
        height=632,
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
        key="data_editor_key", 
        on_change=sync_edits,
        use_container_width=True)
    return st.session_state.edited_df

def display_lineup(lineup_df):
    with st.container():
        lineup_placeholder = st.empty() 
        lineup_placeholder.dataframe(lineup_df, column_config={'NAME': st.column_config.Column(width=134)}, height=352, hide_index=True, use_container_width=True)
    return lineup_placeholder

def lock_player_errors():
    errors = []
    edited_df = st.session_state.edited_df
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
    for e in errors: 
        st.error(e)  

def customize_constraints(input_controls, edited_df):    
    team_constraints = {
        'qb_stacks': [],
        'qb_stacks_opposing': [],
        'RB_DST': input_controls['RB_DST'],
        'dst_exclude_opp': input_controls['dst_exclude_opp'],
        'rb_max': input_controls['rb_max'],
        'flex_team': input_controls['flex_team']
    }    
    player_pos_constraints = {
        'include': edited_df[edited_df['lock']].index.tolist(), 
        'exclude': edited_df[edited_df['exclude']].index.tolist(),
        'flex_req': input_controls['flex_req']
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

def display_results(results, lineup_df):
    final_lineup = lineup_df.copy()    
    for player in results:
        row = final_lineup[(final_lineup["POS"] == results[player]['position']) & (final_lineup["NAME"] == "")].index
        if len(row) > 0:
            final_lineup.at[row[0], "NAME"] = results[player]['name'] 
            final_lineup.at[row[0], "TEAM"] = results[player]['team']
            final_lineup.at[row[0], "PROJ"] = results[player]['projection'] 
            final_lineup.at[row[0], "SAL"] = results[player]['salary']
        else:
            flex_row = final_lineup[(final_lineup["POS"] == "FLEX") & (final_lineup["NAME"] == "")].index
            if len(flex_row) > 0 and results[player]['position'] in ['RB', 'WR', 'TE']:
                final_lineup.at[flex_row[0], "NAME"] = results[player]['name']
                final_lineup.at[flex_row[0], "TEAM"] = results[player]['team']
                final_lineup.at[flex_row[0], "PROJ"] = results[player]['projection']
                final_lineup.at[flex_row[0], "SAL"] = results[player]['salary']
    return final_lineup

run_app()