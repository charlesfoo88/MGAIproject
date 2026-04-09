"""Debug script to see what API-Sports returns for Liverpool match"""
import requests
import os
import json
from dotenv import load_dotenv
from pathlib import Path

# Load .env from Backend folder
backend_dir = Path(__file__).parent.parent
load_dotenv(backend_dir / ".env")

API_KEY = os.getenv('API_SPORTS_KEY')

headers = {
    'x-rapidapi-key': API_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}

# Fetch fixture 1208280 events
response = requests.get(
    'https://v3.football.api-sports.io/fixtures/events',
    headers=headers,
    params={'fixture': 1208280}
)

data = response.json()
events = data['response']

print(f"Total events: {len(events)}\n")

# Filter goals only
goals = [e for e in events if e['type'] == 'Goal']
print(f"Goals: {len(goals)}\n")

for goal in goals:
    print(f"  {goal['team']['name']}")
    print(f"  Player: {goal['player']['name']}")
    print(f"  Minute: {goal['time']['elapsed']}")
    print(f"  Detail: {goal['detail']}")
    print()
