import requests
import json
from pulp import *

def fetch_sleeper_players():
    # Fetch projections from sleeper API.
    sleeper_API = requests.get('https://api.sleeper.app/projections/nfl/2023/18?season_type=regular&position%5B%5D=DEF&position%5B%5D=K&position%5B%5D=RB&position%5B%5D=QB&position%5B%5D=TE&position%5B%5D=WR&order_by=ppr')
    sleeper_data = sleeper_API.text 
    json_sleeper_data = json.loads(sleeper_data)
    # Create dictionary of player names and projections.
    sleeper_players = {}
    for item in json_sleeper_data:
        projection = item['stats'].get('pts_ppr')
        if projection and item['player']['position'] == 'DEF': 
            sleeper_players.update({item['player']['last_name']: projection})
        elif projection: 
            sleeper_players.update({item['player']['first_name'] + ' ' + item['player']['last_name']: projection})
    return(sleeper_players)

def fetch_dk_players(): 
    # Fetch contest data from DraftKings API. 
    dk_API = requests.get('https://api.draftkings.com/draftgroups/v1/draftgroups/98582/draftables')
    dk_data = dk_API.text 
    json_dk_data = json.loads(dk_data)
    sleeper_players = fetch_sleeper_players()   
    dk_players = []
    salaries = {'QB':{}, 'RB':{}, 'WR':{}, 'TE':{}, 'DST':{}}
    projections = {'QB':{}, 'RB':{}, 'WR':{}, 'TE':{}, 'DST':{}}
    for index, item in enumerate(json_dk_data['draftables']):
        if item['draftStatAttributes'][0].get('id') == 90:                
            if index != len(json_dk_data['draftables'])-1 and item['playerId'] != json_dk_data['draftables'][index + 1]['playerId']:
                # Match sleeper projection to player.
                for key, value in sleeper_players.items():
                    if item['displayName'] == key or item['displayName'][:15] == key[:15]:
                        # Add player to salary and projection dictionaries. 
                        info = {'num': index, 'name': item['displayName'], 'position': item['position'], 'salary': item['salary'], 'projection': value}
                        dk_players.append(info)
                        salaries[item['position']].update({item['displayName']: item['salary']})
                        projections[item['position']].update({item['displayName']: value})
                        # Add flex player duplicate. 
                        if item['position'] in ('RB', 'WR', 'TE'):
                            new_info = {'num': index, 'name': item['displayName'], 'position': 'FLEX', 'salary': item['salary'], 'projection': value}
                            dk_players.append(new_info)
    # Define PuLP optimizer problem and variables. 
    prob = LpProblem("Optimize DFS", LpMaximize)
    _vars = {k: LpVariable.dict(k, v, cat="Binary") for k, v in projections.items()}   
    # Set constraint and sum variables for position, salary, and projection. 
    pos_max = {
        'QB': 1,
        'RB': 3,
        'WR': 4,
        'TE': 2,
        'DST': 1
    }
    salary_max = 50000
    prices = []
    points = []
    flex_total = []
    flex_pos = {
        'QB': 0,
        'RB': 1,
        'WR': 1,
        'TE': 1,
        'DST': 0
    }
    # Get salary, projection, and position totals and define PuLP optimizer constraints.
    for k, v in _vars.items():
        prices += lpSum([salaries[k][i] * _vars[k][i] for i in v])
        points += lpSum([projections[k][i] * _vars[k][i] for i in v])
        prob +=  lpSum([_vars[k][i] for i in v]) <= pos_max[k] 
        flex_total += lpSum([flex_pos[k] * _vars[k][i] for i in v]) 
    prob += lpSum(flex_total) == 7
    prob += lpSum(points)
    prob += lpSum(prices) <= salary_max
    # Solve PuLP optimizer. 
    prob.solve()
    # Print PuLP optimizer results of players with salaries and projections. 
    flex_count = {'RB': 0, 'WR': 0, 'TE': 0}
    sal_used = 0
    for v in prob.variables():
        if v.varValue == 1:
            parts = v.name.split('_')
            pos = parts[0]
            sal = salaries[pos][' '.join(parts[1:])]
            proj = projections[pos][' '.join(parts[1:])]
            sal_used += sal
            if pos in ['RB', 'WR', 'TE'] and flex_count[pos] == pos_max[pos] - 1:
                print(f"FLEX_{v.name} - Salary ${sal}, Projection {proj} ")
            elif pos in ['RB', 'WR', 'TE']:
                flex_count[pos] += 1
                print(f"{v.name} - Salary ${sal}, Projection {proj}")
            else:
                print(f"{v.name} - Salary ${sal}, Projection {proj}")
    print(f"Projected Total: {pulp.value(prob.objective)}")
    print(f"Remaining Salary: ${50000-sal_used}")
fetch_dk_players()