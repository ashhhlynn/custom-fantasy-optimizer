import requests
import json
from datetime import datetime, timedelta, timezone
import pytz

def fetch_player_data():
    dk_sports_API = requests.get('https://www.draftkings.com/lobby/getcontests?sport=nfl')
    json_dk_sports_data = json.loads(dk_sports_API.text)
    classic_contest = next((contest for contest in json_dk_sports_data['Contests'] if contest.get('gameType') == 'Classic' and contest.get('sdstring', '')[:3] == 'Sun'), None)
    nfl_week = get_current_nfl_week()
    if nfl_week >= 18:
        week = 18
        dg = 139525
    else:
        week = nfl_week
        dg = classic_contest['dg']     
    sleeper_players = fetch_sleeper_projections(week)       
    dk_players, teams, games, logos, game_times = fetch_dk_players(sleeper_players, dg)
    return(dk_players, teams, games, logos, game_times)

def get_current_nfl_week():
    today = datetime.now()
    sept_first = datetime(2025, 9, 1)
    first_monday = sept_first + timedelta(days=(7 - sept_first.weekday()) % 7)
    nfl_week = ((today - first_monday).days // 7) + 1
    return(nfl_week)

def fetch_sleeper_projections(week):
    sleeper_API = requests.get(f"https://api.sleeper.app/projections/nfl/2025/{week}?season_type=regular&position%5B%5D=DEF&position%5B%5D=K&position%5B%5D=RB&position%5B%5D=QB&position%5B%5D=TE&position%5B%5D=WR&order_by=ppr")
    json_sleeper_data = json.loads(sleeper_API.text)    
    sleeper_players = {}
    for item in json_sleeper_data:
        projection = item['stats'].get('pts_ppr')
        if projection and item['player']['position'] == 'DEF': 
            sleeper_players.update({item['player']['last_name']: projection})
        elif projection: 
            sleeper_players.update({item['player']['first_name'] + ' ' + item['player']['last_name']: projection})
    return(sleeper_players)

def fetch_dk_players(sleeper_players, dg): 
    dk_API = requests.get(f"https://api.draftkings.com/draftgroups/v1/draftgroups/{dg}/draftables")
    json_dk_data = json.loads(dk_API.text)
    dk_players = {}
    teams = {}   
    games = {}
    logos = {}
    game_times = {}
    for index, item in enumerate(json_dk_data['draftables']):
        if item['draftStatAttributes'][0].get('id') == 90 and (index == 0 or item['playerId'] != json_dk_data['draftables'][index - 1]['playerId']):
            parts = item['competition']['name'].split('@')
            injury = 'O' if item['status'] == 'OUT' else item['status']
            opponent = parts[0].strip() if parts[1].strip() == item['teamAbbreviation'] else parts[1].strip() 
            info = {str(index): {
                'name': item['displayName'],
                'position': item['position'], 
                'team': item['teamAbbreviation'], 
                'opp': opponent, 
                'FPPG': item['draftStatAttributes'][0]['value'], 
                'OPRK': item['draftStatAttributes'][1]['value'], 
                'salary': item['salary'], 
                'projection': 0,    
                'status': injury
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
                logos.update({item['teamAbbreviation']: f"https://a.espncdn.com/i/teamlogos/nfl/500/{item['teamAbbreviation'].lower()}.png"})
                if opponent not in games:
                    games.update({item['teamAbbreviation']: opponent})
                    dt = item['competition']['startTime'].split(".")[0] + "Z"
                    dt_utc = datetime.strptime(dt, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    central_time = dt_utc.astimezone(pytz.timezone('America/Chicago'))
                    formatted_time = central_time.strftime('%b %d, %I:%M')
                    game_times.update({item['teamAbbreviation']: formatted_time})
    return(dk_players, teams, games, logos, game_times)