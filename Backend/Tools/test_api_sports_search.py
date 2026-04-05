"""Test api-sports.io - broader search for Arsenal matches"""
import requests
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('API_SPORTS_KEY')
BASE_URL = 'https://v3.football.api-sports.io'
headers = {'x-apisports-key': API_KEY}

print("=" * 60)
print("API-SPORTS.IO - ARSENAL MATCHES SEARCH")
print("=" * 60)

# Try different approaches to find matches

print("\n[Approach 1] Search by team + season...")
params = {
    'league': 39,  # Premier League
    'season': 2024,
    'team': 42  # Arsenal team ID
}
response = requests.get(f'{BASE_URL}/fixtures', headers=headers, params=params)
data = response.json()
print(f"Season 2024: {data.get('results', 0)} matches found")

if data.get('results', 0) > 0:
    print("\nFirst 10 Arsenal matches in 2024/25 season:")
    for match in data['response'][:10]:
        home = match['teams']['home']['name']
        away = match['teams']['away']['name']
        date = match['fixture']['date'][:10]
        status = match['fixture']['status']['short']
        fixture_id = match['fixture']['id']
        
        score_home = match['goals']['home'] if match['goals']['home'] is not None else '-'
        score_away = match['goals']['away'] if match['goals']['away'] is not None else '-'
        
        print(f"  {date} | {home} vs {away} | {score_home}-{score_away} | {status} | ID: {fixture_id}")
        
        # Check for our target matches
        if 'Arsenal' in home and 'Manchester City' in away and score_home == 5 and score_away == 1:
            print(f"    ^^^ FOUND Arsenal 5-1 Man City!")
        if ('Liverpool' in home and 'Manchester City' in away) or ('Manchester City' in home and 'Liverpool' in away):
            if (score_home == 2 and score_away == 0) or (score_home == 0 and score_away == 2):
                print(f"    ^^^ FOUND Liverpool 2-0 Man City!")

print("\n[Approach 2] Search by date range (Jan-Mar 2025)...")
params = {
    'league': 39,
    'season': 2024,
    'from': '2025-01-01',
    'to': '2025-03-31',
    'team': 42
}
response = requests.get(f'{BASE_URL}/fixtures', headers=headers, params=params)
data = response.json()
print(f"Jan-Mar 2025: {data.get('results', 0)} matches found")

if data.get('results', 0) > 0:
    print("\nArsenal matches in Jan-Mar 2025:")
    for match in data['response']:
        home = match['teams']['home']['name']
        away = match['teams']['away']['name']
        date = match['fixture']['date'][:10]
        score_home = match['goals']['home'] if match['goals']['home'] is not None else '-'
        score_away = match['goals']['away'] if match['goals']['away'] is not None else '-'
        fixture_id = match['fixture']['id']
        
        print(f"  {date} | {home} vs {away} | {score_home}-{score_away} | ID: {fixture_id}")
        
        if 'Manchester City' in away and score_home == 5 and score_away == 1:
            print(f"    ^^^ TARGET FOUND!")

print("\n" + "=" * 60)
print(f"API calls used: Check /status endpoint")
print("=" * 60)
