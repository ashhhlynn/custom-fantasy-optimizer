import requests
import json
from pulp import *

def fetch_sleeper_players():
    # Fetch projections from sleeper API.
    sleeper_API = requests.get('https://api.sleeper.app/projections/nfl/2023/18?season_type=regular&position%5B%5D=DEF&position%5B%5D=K&position%5B%5D=RB&position%5B%5D=QB&position%5B%5D=TE&position%5B%5D=WR&order_by=ppr')
    json_sleeper_data = json.loads(sleeper_API.text)    
    # Create dictionary of sleeper names and projections. 
    sleeper_players = {}
    for item in json_sleeper_data:
        projection = item['stats'].get('pts_ppr')
        if projection and item['player']['position'] == 'DEF': 
            sleeper_players.update({item['player']['last_name']: projection})
        elif projection: 
            sleeper_players.update({item['player']['first_name'] + ' ' + item['player']['last_name']: projection})
    return sleeper_players

def fetch_dk_players(): 
    # Fetch contest data from DraftKings API. 
    dk_API = requests.get('https://api.draftkings.com/draftgroups/v1/draftgroups/98582/draftables')
    json_dk_data = json.loads(dk_API.text)
    sleeper_players = fetch_sleeper_players()       
    dk_players = {}
    # Loop through players and skip duplicates. 
    for index, item in enumerate(json_dk_data['draftables']):
        if item['draftStatAttributes'][0].get('id') == 90:                
            if index == 0 or item['playerId'] != json_dk_data['draftables'][index - 1]['playerId']:
                parts = item['competition']['name'].split('@')
                opp = parts[0].strip() if parts[1].strip() == item['teamAbbreviation'] else parts[1].strip() 
                # Match sleeper projection to player.
                if item['displayName'] in sleeper_players:
                    dk_players.update({str(index): {'name': item['displayName'], 'position': item['position'], 'team': item['teamAbbreviation'], 'opp': opp, 'salary': item['salary'], 'projection': sleeper_players[item['displayName']]}})
                elif item['displayName'][:15] in sleeper_players:
                    dk_players.update({str(index): {'name': item['displayName'], 'position': item['position'], 'team': item['teamAbbreviation'], 'opp': opp, 'salary': item['salary'], 'projection': sleeper_players[item['displayName'][:15]]}})
    return dk_players

def optimize_dk_players(flex_input, incl_input, excl_input, qb_stack_input, dst_stack_input):
    dk_players = fetch_dk_players()  
    # Define PuLP problem and variable. 
    prob = LpProblem('Optimize', LpMaximize)
    player_vars = LpVariable.dicts('Select', dk_players.keys(), 0, 1, cat='Binary')
    # Define PuLP constraints for maximum salary and players per position. 
    pos_max = {
        'QB': 1,
        'RB': 3,
        'WR': 4,
        'TE': 2,
        'DST': 1
    }
    prob += lpSum(dk_players[p]["salary"] * player_vars[p] for p in dk_players) <= 50000
    prob += lpSum(player_vars[p] for p in dk_players) == 9  
    prob += lpSum(player_vars[p] for p in dk_players if dk_players[p]['position'] in ["RB", "WR", "TE"]) == 7  
    # Require inclusion or exclusion of players if specified.
    for p in incl_input:
        if p in player_vars:
            player_vars[p].lowBound = 1
    for p in excl_input:
        if p in player_vars:
            player_vars[p].upBound = 0
    for pos, max_count in pos_max.items():
        prob += lpSum([player_vars[p] for p in dk_players if dk_players[p]['position'] == pos]) <= max_count
        # Require position for flex if specified and update PuLP constraints for players per flex position.
        if flex_input in ["RB", "WR", "TE"] and flex_input == pos:
            prob += lpSum([player_vars[p] for p in dk_players if dk_players[p]['position'] == flex_input]) == max_count
        elif flex_input in ["RB", "WR", "TE"] and pos in ["RB", "WR", "TE"]:
            prob += lpSum([player_vars[p] for p in dk_players if dk_players[p]['position'] == pos]) == max_count - 1   
    # Define PuLP constraints for maximum players per team.  
    team_constraints(dk_players, player_vars, prob, qb_stack_input, dst_stack_input)
    # Define PuLP objective to maximize total projection and solve. 
    prob += lpSum(dk_players[p]["projection"] * player_vars[p] for p in dk_players)
    prob.solve()
    # Print PuLP results of players with salaries and projections. 
    flex_count = {'RB': 0, 'WR': 0, 'TE': 0}    
    for player in dk_players:
        if player_vars[player].varValue == 1:
            pos = dk_players[player]['position']
            # Label flex if RB, WR, or TE player count reaches position maximum. 
            if pos in ['RB', 'WR', 'TE'] and flex_count[pos] == pos_max[pos] - 1:
                print(f"FLEX {dk_players[player]['name']} ({dk_players[player]['team']} {player}): ${dk_players[player]['salary']}, {dk_players[player]['projection']}")
            elif pos in ['RB', 'WR', 'TE']:
                print(f"{pos} {dk_players[player]['name']} ({dk_players[player]['team']} {player}): ${dk_players[player]['salary']}, {dk_players[player]['projection']}")
                flex_count[pos] += 1
            else:
                print(f"{pos} {dk_players[player]['name']} ({dk_players[player]['team']} {player}): ${dk_players[player]['salary']}, {dk_players[player]['projection']}")
                print(dk_players[player])
    print("Total Projection:", pulp.value(prob.objective))
    print("Remaining Salary:", 50000 - sum(dk_players[p]["salary"] * player_vars[p].varValue for p in dk_players))

def team_constraints(dk_players, player_vars, prob, qb_stack_input, dst_stack_input):
    teams = {}
    for data in dk_players.values():
        teams.update({data['team']: {'RB':0, 'WR':0, 'TE':0}}) if data["position"] == 'DST' else None
    for team in teams: 
        # Require QB + RB, WR, and/or TE from the same team if specified.
        for pos in qb_stack_input:
            flex = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == pos])  
            qb = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == "QB"])
            prob += lpSum(flex) >= lpSum(qb)
        # Require DST + RB from the same team if specified. 
        dst = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == "DST"])
        if dst_stack_input[0] == 1:
            rb = lpSum([player_vars[k] for k in dk_players if dk_players[k]['team'] == team and dk_players[k]['position'] == 'RB'])  
            prob += lpSum(rb) >= lpSum(dst)
        # Require exclusion of teams opposing DST if specified.  
        if dst_stack_input[1] == 1:
            other = lpSum([player_vars[k] for k in dk_players if dk_players[k]['opp'] == team and dk_players[k]['position'] != 'DST'])  
            prob += lpSum(lpSum(other)) if lpSum(dst) >= 1 else None == 0

# Option to require specific position for flex.
flex_input = ''
# Option to require inclusion or exclusion of specific players. 
incl_input = ['111']
excl_input = ['61']
# Option to require QB + RB, WR, and/or TE stacks from the same team.
qb_stack_input = ['WR']
# Options to require DST + RB stack from the same team and exclusion of teams opposing DST. 
dst_stack_input = [1,0]

optimize_dk_players(flex_input, incl_input, excl_input, qb_stack_input, dst_stack_input)