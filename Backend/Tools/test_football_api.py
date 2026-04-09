"""Test api-football (api-sports.io) for match events and generate MGAI soccer JSON"""
import requests
import json
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()
api_key = os.getenv('API_FOOTBALL_KEY')
headers = {
    'x-apisports-key': api_key
}
BASE_URL = 'https://v3.football.api-sports.io'

# Load template
template_path = Path(__file__).parent.parent / "Mock_Data" / "mgai_soccer_event_template.json"
with open(template_path, 'r') as f:
    template = json.load(f)

print("=" * 60)
print("API-FOOTBALL TEST")
print("=" * 60)

# Step 1 — Find match IDs for both matches
print("\n[Step 1] Finding matches...")
target_matches = {}

# Arsenal vs Man City (Feb 2, 2025)
print("\n  Searching Arsenal matches (Jan-Mar 2025)...")
params = {
    'league': 39,
    'season': 2024,
    'from': '2025-02-01',
    'to': '2025-02-03',
    'team': 42  # Arsenal team ID
}
response = requests.get(f'{BASE_URL}/fixtures', headers=headers, params=params)
data = response.json()
fixtures = data.get('response', [])
print(f"  Found {len(fixtures)} Arsenal fixtures")

for f in fixtures:
    home = f['teams']['home']['name']
    away = f['teams']['away']['name']
    goals_h = f['goals']['home']
    goals_a = f['goals']['away']
    fixture_id = f['fixture']['id']
    venue = f['fixture']['venue']['name']
    date = f['fixture']['date'][:10]
    
    print(f"    {date} | {home} vs {away} | {goals_h}-{goals_a} | ID: {fixture_id}")
    
    if 'Manchester City' in away and goals_h == 5 and goals_a == 1:
        target_matches['arsenal_5_1_man_city_2025_02_02'] = {
            'fixture_id': fixture_id,
            'home_team': home,
            'away_team': away,
            'final_score': f"{goals_h}-{goals_a}",
            'venue': venue,
            'date': date
        }
        print(f"      ^^^ TARGET FOUND!")

# Liverpool 2-0 Man City (Feb 23, 2025) - City are away
print("\n  Searching Man City away matches (Feb 20-25, 2025)...")
params = {
    'league': 39,
    'season': 2024,
    'from': '2025-02-20',
    'to': '2025-02-25',
    'team': 50  # Man City team ID
}
response = requests.get(f'{BASE_URL}/fixtures', headers=headers, params=params)
data = response.json()
fixtures = data.get('response', [])
print(f"  Found {len(fixtures)} Man City fixtures")

for f in fixtures:
    home = f['teams']['home']['name']
    away = f['teams']['away']['name']
    goals_h = f['goals']['home']
    goals_a = f['goals']['away']
    fixture_id = f['fixture']['id']
    venue = f['fixture']['venue']['name']
    date = f['fixture']['date'][:10]
    
    print(f"    {date} | {home} vs {away} | {goals_h}-{goals_a} | ID: {fixture_id}")
    
    if ('Liverpool' in home and 'Manchester City' in away and goals_h == 2 and goals_a == 0) or \
       ('Manchester City' in home and 'Liverpool' in away and goals_h == 0 and goals_a == 2):
        target_matches['liverpool_2_0_man_city_2025_02_23'] = {
            'fixture_id': fixture_id,
            'home_team': home,
            'away_team': away,
            'final_score': f"{goals_h}-{goals_a}",
            'venue': venue,
            'date': date
        }
        print(f"      ^^^ TARGET FOUND!")

# Step 2 — Get events for each match
for match_key, match_info in target_matches.items():
    fixture_id = match_info['fixture_id']
    print(f"\n[Step 2] Getting events for {match_key}...")

    url = f'{BASE_URL}/fixtures/events'
    params = {'fixture': fixture_id}
    response = requests.get(url, headers=headers, params=params)
    events_data = response.json().get('response', [])
    print(f"  ✓ Found {len(events_data)} events")

    # Print all events
    for e in events_data:
        minute = e['time']['elapsed']
        team = e['team']['name']
        player = e['player']['name'] if e.get('player') else 'N/A'
        assist = e['assist']['name'] if e.get('assist') else None
        event_type = e['type']
        detail = e['detail']
        print(f"    {minute}' | {team} | {player} | {event_type} | {detail}")

    # Step 3 — Build MGAI JSON matching template structure
    print(f"\n[Step 3] Generating MGAI JSON...")

    entity_registry = [
        {
            "entity_id": f"team_{match_info['home_team'].lower().replace(' ', '_')}",
            "entity_type": "team",
            "canonical_name": match_info['home_team'],
            "aliases": [match_info['home_team'], match_info['home_team'].split()[0]],
            "team_id": match_info['home_team'].lower().replace(' ', '_')
        },
        {
            "entity_id": f"team_{match_info['away_team'].lower().replace(' ', '_')}",
            "entity_type": "team",
            "canonical_name": match_info['away_team'],
            "aliases": [match_info['away_team'], match_info['away_team'].split()[-1]],
            "team_id": match_info['away_team'].lower().replace(' ', '_')
        }
    ]

    score_progression = [{"time": "0:00", "score": "0-0", "event": "kickoff"}]
    mgai_events = []
    event_counter = 1
    seen_players = set()
    current_home = 0
    current_away = 0
    home_team = match_info['home_team']

    for e in events_data:
        minute = e['time']['elapsed']
        team = e['team']['name']
        player = e['player']['name'] if e.get('player') and e['player'].get('name') else 'Unknown'
        assist = e['assist']['name'] if e.get('assist') and e['assist'].get('name') else None
        event_type = e['type']
        detail = e['detail']
        match_phase = "first_half" if minute <= 45 else "second_half"

        # Map event type
        if event_type == 'Goal':
            if detail == 'Own Goal':
                mgai_type = 'own_goal'
            elif detail == 'Penalty':
                mgai_type = 'penalty_goal'
            else:
                mgai_type = 'goal'
            if team == home_team:
                current_home += 1
            else:
                current_away += 1
            score_display = f"{current_home}-{current_away}"
            score_progression.append({
                "time": f"{minute}:00",
                "score": score_display,
                "scorer": player,
                "team": team,
                "event": "goal"
            })
            importance = 0.95
            emotion_tags = ["excitement", "celebration"]
        elif event_type == 'subst':
            mgai_type = 'substitution'
            score_display = None
            importance = 0.5
            emotion_tags = ["neutral"]
        elif event_type == 'Card':
            mgai_type = 'card'
            score_display = None
            importance = 0.6
            emotion_tags = ["tension"]
        else:
            mgai_type = event_type.lower()
            score_display = None
            importance = 0.5
            emotion_tags = ["neutral"]

        players = [player]
        if assist:
            players.append(assist)

        # Add player to entity registry
        if player and player not in seen_players and player != 'Unknown':
            seen_players.add(player)
            last_name = player.split()[-1]
            entity_registry.append({
                "entity_id": f"player_{last_name.lower()}",
                "entity_type": "player",
                "canonical_name": player,
                "aliases": [last_name, player],
                "team_id": team.lower().replace(' ', '_')
            })

        mgai_events.append({
            "clip_id": f"segment_{str(event_counter).zfill(3)}",
            "time": f"{minute}:00",
            "time_seconds": float(minute * 60),
            "event_type": mgai_type,
            "importance": importance,
            "confidence": 0.99,
            "team": team,
            "players": players,
            "score_after_event": score_display,
            "clip_start_sec": None,
            "clip_end_sec": None,
            "ocr_text": [player, f"{minute}:00"],
            "match_phase": match_phase,
            "context": {
                "previous_event": None,
                "next_event": None,
                "narrative": f"{player} — {detail} for {team} at {minute} minutes."
            }
        })
        event_counter += 1

    # Build final MGAI JSON
    mgai_json = {
        "match_context": {
            "match_id": str(fixture_id),
            "home_team": match_info['home_team'],
            "away_team": match_info['away_team'],
            "competition": "Premier League",
            "venue": match_info['venue'],
            "match_date": match_info['date'],
            "final_score": match_info['final_score'],
            "season": "2024-2025"
        },
        "entity_registry": entity_registry,
        "score_progression": score_progression,
        "events": mgai_events
    }

    # Save
    output_dir = Path(__file__).parent.parent / "Mock_Data" / match_key
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "approach_b_dl_handoff.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(mgai_json, f, indent=2, ensure_ascii=False)

    print(f"  ✓ {len(mgai_events)} events generated")
    print(f"  ✓ Saved to: {output_path}")
    print(f"\n  Score progression:")
    for s in score_progression:
        print(f"    {s}")

print("\n" + "=" * 60)
print("✅ DONE")
print("=" * 60)
