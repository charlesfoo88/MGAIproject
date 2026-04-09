"""Quick script to find fixture ID for a match"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('API_SPORTS_KEY')
headers = {
    'x-rapidapi-key': API_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}

# Liverpool = 40, Man City = 50
# Search for matches between these teams in February 2025
response = requests.get(
    'https://v3.football.api-sports.io/fixtures',
    headers=headers,
    params={
        'team': 40,  # Liverpool
        'season': 2024,  # 2024-2025 season
        'from': '2024-11-28',
        'to': '2024-12-04'
    }
)

data = response.json()
print(f"\nAPI Status: {data.get('results', 0)} results found")

if data.get('response'):
    for fixture in data['response']:
        home = fixture['teams']['home']['name']
        away = fixture['teams']['away']['name']
        home_id = fixture['teams']['home']['id']
        away_id = fixture['teams']['away']['id']
        
        # Check if it's Liverpool vs Man City
        if (home_id == 40 and away_id == 50) or (home_id == 50 and away_id == 40):
            fixture_id = fixture['fixture']['id']
            date = fixture['fixture']['date']
            score = f"{fixture['goals']['home']}-{fixture['goals']['away']}"
            
            print(f"\n✅ FOUND: {home} vs {away}")
            print(f"   Fixture ID: {fixture_id}")
            print(f"   Date: {date}")
            print(f"   Score: {score}")
else:
    print("No matches found. Response:", data)
