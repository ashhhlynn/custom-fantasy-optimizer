import requests
import json

def fetch_sleeper_projections():
    sleeper_API = requests.get('https://api.sleeper.app/projections/nfl/2025/8?season_type=regular&position%5B%5D=DEF&position%5B%5D=K&position%5B%5D=RB&position%5B%5D=QB&position%5B%5D=TE&position%5B%5D=WR&order_by=ppr')
    json_sleeper_data = json.loads(sleeper_API.text)    
    sleeper_players = {}
    for item in json_sleeper_data:
        projection = item['stats'].get('pts_ppr')
        if projection and item['player']['position'] == 'DEF': 
            sleeper_players.update({item['player']['last_name']: projection})
        elif projection: 
            sleeper_players.update({item['player']['first_name'] + ' ' + item['player']['last_name']: projection})
    return(sleeper_players)

def fetch_dk_players(sleeper_players): 
    dk_API = requests.get('https://api.draftkings.com/draftgroups/v1/draftgroups/134062/draftables')
    json_dk_data = json.loads(dk_API.text)
    dk_players = {}
    team_games = {}    
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
                'projection':0,
                'status': item['status']
            }}
            if item['displayName'] in sleeper_players:
                info[str(index)]['projection'] = sleeper_players[item['displayName']]
            elif len(item['displayName'].split(' ', 2)) > 2:
                short = ' '.join(item['displayName'].split(' ', 2)[:2])
                if short in sleeper_players:
                    info[str(index)]['projection'] = sleeper_players[short]
            dk_players.update(info)
            if item['position'] == 'DST' and item['teamAbbreviation'] not in team_games:
                team_games.update({item['teamAbbreviation']: opponent})            
    return(dk_players, team_games)

def get_games_logos(team_games):
    games = {}
    logos = {}
    for team, opponent in team_games.items():
        if opponent not in games:
            games.update({team: opponent})
        logos.update({team: f"https://a.espncdn.com/i/teamlogos/nfl/500/{team.lower()}.png"})
    return(games, logos)