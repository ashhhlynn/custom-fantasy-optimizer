import requests
import json

def fetch_sleeper_players():
    # fetch sleeper API
    sleeper_API = requests.get('https://api.sleeper.app/projections/nfl/2023/18?season_type=regular&position%5B%5D=DEF&position%5B%5D=K&position%5B%5D=RB&position%5B%5D=QB&position%5B%5D=TE&position%5B%5D=WR&order_by=ppr')
    sleeper_data = sleeper_API.text 
    json_sleeper_data = json.loads(sleeper_data)
    # list players with name and projection keys
    sleeper_players = []
    for item in json_sleeper_data:
        projection = item['stats'].get('pts_ppr')
        if projection and item['player']['position'] == 'DEF': 
            sleeper_players.append({item['player']['last_name']: projection})
        elif projection: 
            sleeper_players.append({item['player']['first_name'] + ' ' + item['player']['last_name']: projection})
    return(sleeper_players)

def fetch_dk_players(): 
    # fetch draftkings API 
    dk_API = requests.get('https://api.draftkings.com/draftgroups/v1/draftgroups/98582/draftables')
    dk_data = dk_API.text 
    json_dk_data = json.loads(dk_data)
    sleeper_players = fetch_sleeper_players()
    dk_players = []
    dk_players_full = []   
    for index, item in enumerate(json_dk_data['draftables']):
        if item['draftStatAttributes'][0].get('id') == 90:                
            if index != len(json_dk_data['draftables'])-1 and item['playerId'] == json_dk_data['draftables'][index + 1]['playerId']:
                # find matching sleeper player projection
                for m in sleeper_players:
                    if item['displayName'] in m:
                        projection = m[item['displayName']] 
                        # add player with position key 
                        info = {index: 1, item['position']: 1, 'projection': projection}
                        new_player = {**item, **info}                
                        dk_players.append(new_player)
                        dk_players_full.append(new_player)
                        # add duplicate player with flex key 
                        flex_info = {index+1000: 1, 'FLEX':1, item['position']:0, 'projection': projection}
                        new_flex = {**item, **flex_info}
                        dk_players_full.append(new_flex)
    print(dk_players)
fetch_dk_players()      