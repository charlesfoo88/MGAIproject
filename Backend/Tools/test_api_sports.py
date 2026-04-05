"""Test api-sports.io (v3.football) for match events"""
import requests
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('API_SPORTS_KEY')
BASE_URL = 'https://v3.football.api-sports.io'
headers = {
    'x-apisports-key': API_KEY
}

print("=" * 60)
print("API-SPORTS.IO TEST")
print("=" * 60)

# Step 1 — Test account status
print("\n[Step 1] Checking API status...")
response = requests.get(f'{BASE_URL}/status', headers=headers)
status = response.json()
print(json.dumps(status, indent=2))

# Step 2 — Find Arsenal vs Man City (Feb 2, 2025)
print("\n[Step 2] Searching for Arsenal vs Man City (Feb 2, 2025)...")
params = {
    'league': 39,  # Premier League
    'season': 2024,
    'date': '2025-02-02'
}
response = requests.get(f'{BASE_URL}/fixtures', headers=headers, params=params)
data = response.json()

print(f"API Response: {data.get('results', 0)} matches found")
if data.get('results', 0) > 0:
    for match in data['response']:
        home = match['teams']['home']['name']
        away = match['teams']['away']['name']
        score_home = match['goals']['home']
        score_away = match['goals']['away']
        fixture_id = match['fixture']['id']
        print(f"\n  {home} vs {away} | {score_home}-{score_away}")
        print(f"  Fixture ID: {fixture_id}")
        
        if 'Arsenal' in home and 'Manchester City' in away:
            print(f"\n[Step 3] Getting events for Arsenal 5-1 Man City...")
            
            # Get fixture events
            events_response = requests.get(
                f'{BASE_URL}/fixtures/events',
                headers=headers,
                params={'fixture': fixture_id}
            )
            events_data = events_response.json()
            
            print(f"\n  Events found: {events_data.get('results', 0)}")
            if events_data.get('results', 0) > 0:
                print("\n  Event details:")
                for event in events_data['response'][:10]:  # First 10 events
                    time = event['time']['elapsed']
                    team = event['team']['name']
                    event_type = event['type']
                    detail = event['detail']
                    player = event['player']['name'] if event.get('player') else 'Unknown'
                    print(f"    {time}' - {event_type}: {detail} by {player} ({team})")
            
            # Get fixture statistics
            stats_response = requests.get(
                f'{BASE_URL}/fixtures/statistics',
                headers=headers,
                params={'fixture': fixture_id}
            )
            stats_data = stats_response.json()
            
            print(f"\n  Statistics found: {stats_data.get('results', 0)}")
            if stats_data.get('results', 0) > 0:
                print("\n  Match statistics:")
                for team_stats in stats_data['response']:
                    team_name = team_stats['team']['name']
                    print(f"\n    {team_name}:")
                    for stat in team_stats['statistics'][:5]:  # First 5 stats
                        print(f"      {stat['type']}: {stat['value']}")
            
            # Save full response for analysis
            output_path = Path(__file__).parent.parent / "Outputs" / "api_sports_full_response.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'fixture': match,
                    'events': events_data,
                    'statistics': stats_data
                }, f, indent=2, ensure_ascii=False)
            
            print(f"\n  ✓ Full response saved to: {output_path}")

print("\n" + "=" * 60)
print("✅ API-SPORTS.IO TEST COMPLETE")
print("=" * 60)
