import pandas as pd 
import streamlit as st 
from streamlit_searchbox import st_searchbox
from data import fetch_player_data
from optimizer import position_bounds, optimize_dk_players

lineup_df = pd.DataFrame({
    'POS': ['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'FLEX', 'DST'],
    'NAME': ['']*9,
    'TEAM': ['']*9,
    'SAL': ['']*9,
    'PROJ': ['']*9,
}) 

def run_app():
    dk_players, teams, games, logos = fetch_player_data()
    players_df = pd.DataFrame.from_dict(dk_players, orient='index')
    players_df['lock'] = False
    players_df['exclude'] = False
    load_streamlit(dk_players, players_df, teams, games, logos)

def load_streamlit(dk_players, players_df, teams, games, logos):
    st.set_page_config(layout='wide')
    display_game_button_logos(games, logos)
    st.markdown(' ')
    st.markdown(' ')    
    col_a, col_b, col_c = st.columns([24,2,12])
    with col_a:
        selected_value, position_filter = display_queue_filters(players_df)
        display_players_queue(players_df, position_filter, selected_value)
    with col_c:
        input_controls = display_input_controls(teams)
        lock_player_errors()
        lineup_placeholder = display_lineup()
        col_g, col_h, col_i, col_j = st.columns([6,3,5,3], vertical_alignment='center')
        col_i.write(f"**Projection**  \n**Rem. Salary**")
        if col_g.button('Optimize', use_container_width=True, type='primary'):
            results, rem_sal, total_proj, status = optimize_dk_players(dk_players, teams, input_controls)
            final_lineup = display_results(results)
            lineup_placeholder.dataframe(
                final_lineup, 
                height=352, 
                column_config={'SAL': st.column_config.NumberColumn(format='$%d'), 'NAME': st.column_config.Column(width=134)}, 
                hide_index=True, 
                use_container_width=True, )
            if status != 'Optimal':
                st.warning('Error: Optimal solution not found.')
            with col_j:
                st.write(round(total_proj, 1), '  \n', rem_sal)
        else:
            with col_j:
                st.write(0.00, '  \n', 50000)

def display_game_button_logos(games, logos):    
    cols = st.columns(9) 
    if 'selected_game' not in st.session_state:
        st.session_state.selected_game = 'All Games'  
    for i, (t, o) in enumerate(games.items()):
        with cols[i % 7 + 1].container(border=True, height=82, gap=None, vertical_alignment='center', horizontal_alignment='right'):
            t_abbr = t if len(t) == 3 else t + '&nbsp;&nbsp;'
            o_abbr = o if len(o) == 3 else o + '&nbsp;&nbsp;'
            col_b1, col_b2 = st.columns([2,3])
            with col_b1:
                st.image(logos[t], width=16)
                st.image(logos[o], width=16)
            if col_b2.button(f"**{t_abbr}  \n{o_abbr}**", type='tertiary'):
                if st.session_state.selected_game == [t, o]:            
                    st.session_state.selected_game = 'All Games'
                else: 
                    st.session_state.selected_game = [t, o]  
        if i == len(games)-1 and len(games) < 12:
            for n in range(11-i):
                c = (i+1+n) % 7 + 1
                cols[c].container(border=True, height=82, vertical_alignment='center', horizontal_alignment='right')

def display_queue_filters(players_df):
    col_a1, col_a2, col_a3 = st.columns([3,1,2])
    with col_a1:
        def search_data(searchterm: str) -> list:
            if not searchterm:
                return []
            results = players_df[players_df['name'].str.contains(searchterm, case=False)]
            return(results['name'].tolist())            
        selected_value = st_searchbox(search_data, placeholder='Search', key='search_key')
    position_filter = col_a3.selectbox('Filters', ('All', 'QB', 'RB', 'WR', 'TE', 'DST'), label_visibility='collapsed')   
    return(selected_value, position_filter)

def display_players_queue(players_df, position_filter, selected_value):
    if 'players_df' not in st.session_state:
        st.session_state.players_df = players_df
    def sync_edits():
        edited_data = st.session_state.data_editor_key['edited_rows']
        for index, updates in edited_data.items():
            original_index = st.session_state.edited_df.iloc[index].name
            st.session_state.players_df.loc[original_index, updates.keys()] = updates.values()   
    if st.session_state.selected_game != 'All Games' and position_filter != 'All':
        filtered_df = st.session_state.players_df[(st.session_state.players_df['team'].isin(st.session_state.selected_game)) & (st.session_state.players_df['position'] == position_filter)].copy() 
    elif st.session_state.selected_game != 'All Games':
        filtered_df = st.session_state.players_df[st.session_state.players_df['team'].isin(st.session_state.selected_game)].copy() 
    elif position_filter != 'All':
        filtered_df = st.session_state.players_df[st.session_state.players_df['position'] == position_filter].copy() 
    else: 
        filtered_df = st.session_state.players_df.copy()   
    if selected_value:
        filtered_df = st.session_state.players_df[st.session_state.players_df['name'] == selected_value].copy()
    visible_columns = [col for col in players_df.columns if col != 'status']
    filtered_df['name'] = players_df.apply(lambda row: f"{row['name']} ({row['status']})" if row['status'] != 'None' else row['name'], axis=1)
    with st.container():
        st.session_state.edited_df = st.data_editor(
        filtered_df[visible_columns],
        height=632,
        hide_index=True,
        column_config={
            "name": st.column_config.Column("NAME", disabled=True),
            "position": st.column_config.Column("POS", disabled=True),
            "team": st.column_config.Column("TEAM", disabled=True),
            "opp": st.column_config.Column("OPP", disabled=True),
            "FPPG": st.column_config.Column("FPPG", disabled=True),
            "OPRK": st.column_config.Column("OPRK", disabled=True),
            "projection": st.column_config.Column("PROJ", disabled=True),
            "salary": st.column_config.NumberColumn("SAL", format="$%d", disabled=True),
            "lock": st.column_config.CheckboxColumn("🔐"),
            "exclude": st.column_config.CheckboxColumn("🚫")
        },
        key='data_editor_key', 
        on_change=sync_edits,
        use_container_width=True)

def display_input_controls(teams):
    with st.container(border=True):
        col_c1, col_c2 = st.columns([10,1])
        col_c1.write('**Customize**')
        col_c2.write('⚙️')
        with st.expander('Team Stacks'):
            st.caption('Require 2 players from the same team:')
            col_c3, col_c4 = st.columns(2)
            with col_c3:
                qb_rb = st.checkbox('QB + RB')
                qb_wr = st.checkbox('QB + WR')
                qb_te = st.checkbox('QB + TE')
            with col_c4:     
                qb_wr_te = st.checkbox('QB + WR/TE')
                qb_flex = st.checkbox('QB + FLEX')
                dst_rb = st.checkbox('RB + DST')
        with st.expander('Opponent Stacks'):
            st.caption('Require Quarterback and opposing players:')
            qb_rb_opp = st.checkbox('QB + RB', key='rb_opp')
            qb_wr_opp = st.checkbox('QB + WR', key='wr_opp')
            qb_te_opp = st.checkbox('QB + TE', key='te_opp')
        col_c5, col_c6 = st.columns([32,20], vertical_alignment='bottom')
        flex_input = col_c5.segmented_control('FLEX Position and Team (Incl.)', ['RB', 'WR', 'TE'], selection_mode='single')
        flex_team_input = col_c6.selectbox('Flex Team', (teams.keys()), placeholder='Team', label_visibility='collapsed', index=None)        
        dst_excl = st.toggle('Exclude Players Opposing DST')
        rb_max = st.toggle('Maximum 1 RB per Team')
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
                        
def lock_player_errors():
    errors = []
    edited_df = st.session_state.players_df
    edited_df.loc[edited_df['lock'], 'exclude'] = False
    if len(edited_df[edited_df['lock']]) > 9:
        errors.append('❌ You can’t lock more than 9 players.')    
    flex_count = edited_df[edited_df['lock']]['position'].isin(['RB', 'WR', 'TE']).sum()
    if flex_count > 7:
        errors.append('❌ You can’t lock more than 7 FLEX eligible players.')
    for pos, caps in position_bounds.items():
        pos_count = (edited_df[edited_df['lock']]['position'] == pos).sum()
        if pos_count > caps['max']:
            errors.append(f"❌ You can’t lock more than {caps['max']} {pos}(s).")
    for e in errors: 
        st.error(e)  

def display_lineup():
    with st.container():
        lineup_placeholder = st.empty() 
        lineup_placeholder.dataframe(lineup_df, column_config={'NAME': st.column_config.Column(width=134)}, height=352, hide_index=True, use_container_width=True)
    return(lineup_placeholder)

def display_results(results):
    final_lineup = lineup_df.copy()    
    for player in results:
        row = final_lineup[(final_lineup['POS'] == results[player]['position']) & (final_lineup['NAME'] == '')].index
        if len(row) > 0:
            final_lineup.at[row[0], 'NAME'] = results[player]['name'] 
            final_lineup.at[row[0], 'TEAM'] = results[player]['team']
            final_lineup.at[row[0], 'PROJ'] = results[player]['projection'] 
            final_lineup.at[row[0], 'SAL'] = results[player]['salary']
        else:
            flex_row = final_lineup[(final_lineup['POS'] == 'FLEX') & (final_lineup['NAME'] == '')].index
            if len(flex_row) > 0 and results[player]['position'] in ['RB', 'WR', 'TE']:
                final_lineup.at[flex_row[0], 'NAME'] = results[player]['name']
                final_lineup.at[flex_row[0], 'TEAM'] = results[player]['team']
                final_lineup.at[flex_row[0], 'PROJ'] = results[player]['projection']
                final_lineup.at[flex_row[0], 'SAL'] = results[player]['salary']
    return(final_lineup)

run_app()