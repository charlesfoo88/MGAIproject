"""Get detailed events from api-sports.io for Arsenal 5-1 Man City"""
import requests
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('API_SPORTS_KEY')
BASE_URL = 'https://v3.football.api-sports.io'
headers = {'x-apisports-key': API_KEY}

FIXTURE_ID = 1208254  # Arsenal 5-1 Man City

print("=" * 60)
print("ARSENAL 5-1 MAN CITY - EVENT DETAILS")
print("=" * 60)

# Get fixture events
print("\n[1] Getting match events...")
response = requests.get(f'{BASE_URL}/fixtures/events', headers=headers, params={'fixture': FIXTURE_ID})
events_data = response.json()

print(f"Events found: {events_data.get('results', 0)}")
print(f"\nAll events:")
for event in events_data.get('response', []):
    time = event['time']['elapsed']
    extra = f"+{event['time']['extra']}" if event['time'].get('extra') else ""
    team = event['team']['name']
    event_type = event['type']
    detail = event['detail']
    player = event['player']['name'] if event.get('player') else 'Unknown'
    assist = f" (Assist: {event['assist']['name']})" if event.get('assist') and event['assist'].get('name') else ""
    
    print(f"  {time}'{extra} - {event_type}: {detail} by {player}{assist} ({team})")

# Get fixture statistics
print("\n[2] Getting match statistics...")
response = requests.get(f'{BASE_URL}/fixtures/statistics', headers=headers, params={'fixture': FIXTURE_ID})
stats_data = response.json()

print(f"Statistics found: {stats_data.get('results', 0)}")
for team_stats in stats_data.get('response', []):
    team_name = team_stats['team']['name']
    print(f"\n  {team_name}:")
    for stat in team_stats['statistics']:
        print(f"    {stat['type']}: {stat['value']}")

# Get lineups
print("\n[3] Getting lineups...")
response = requests.get(f'{BASE_URL}/fixtures/lineups', headers=headers, params={'fixture': FIXTURE_ID})
lineups_data = response.json()

print(f"Lineups found: {lineups_data.get('results', 0)}")
for lineup in lineups_data.get('response', []):
    team_name = lineup['team']['name']
    formation = lineup['formation']
    print(f"\n  {team_name} ({formation}):")
    print(f"    Starting XI:")
    for player in lineup['startXI'][:11]:
        pos = player['player']['pos']
        name = player['player']['name']
        number = player['player']['number']
        print(f"      {number}. {name} ({pos})")

# Get fixture details
print("\n[4] Getting full fixture details...")
response = requests.get(f'{BASE_URL}/fixtures', headers=headers, params={'id': FIXTURE_ID})
fixture_data = response.json()

# Save everything
output_path = Path(__file__).parent.parent / "Outputs" / "api_sports_arsenal_5_1_man_city_full.json"
full_data = {
    'fixture': fixture_data.get('response', [{}])[0] if fixture_data.get('response') else {},
    'events': events_data.get('response', []),
    'statistics': stats_data.get('response', []),
    'lineups': lineups_data.get('response', [])
}

with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(full_data, f, indent=2, ensure_ascii=False)

print(f"\n✓ Full data saved to: {output_path}")

# Check API usage
response = requests.get(f'{BASE_URL}/status', headers=headers)
status = response.json()
requests_used = status['response']['requests']['current']
requests_limit = status['response']['requests']['limit_day']
print(f"\n✓ API Requests: {requests_used}/{requests_limit} used today")

print("\n" + "=" * 60)
print("✅ COMPLETE - Check the JSON file for full details")
print("=" * 60)
