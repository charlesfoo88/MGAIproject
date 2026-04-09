"""
Approach B Ingestor — Fully Autonomous Match Data Generation

This script:
1. Fetches match events from API-Football (api-sports.io)
2. Maps events to video timestamps using Gemini Vision
3. Generates two output files:
   - approach_b_dl_handoff.json (MGAI standard format)
   - approach_b_highlight_candidates.json (D15 format)

Usage:
    python Backend/Tools/approach_b_ingestor.py --match arsenal_5_1_man_city_2025_02_02 --video test_clip.mp4
"""

import requests
from google import genai
import os
import sys
import time
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# API Configuration
API_FOOTBALL_BASE_URL = 'https://v3.football.api-sports.io'
API_FOOTBALL_KEY = os.getenv('API_FOOTBALL_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not API_FOOTBALL_KEY or not GEMINI_API_KEY:
    print("❌ Error: API keys not found in .env file")
    print("   Required: API_FOOTBALL_KEY, GEMINI_API_KEY")
    sys.exit(1)

# Initialize Gemini client
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# Paths
BACKEND_DIR = Path(__file__).parent.parent
MOCK_DATA_DIR = BACKEND_DIR / "Mock_Data"
SOURCE_VIDEOS_DIR = BACKEND_DIR / "Source_Videos"


def fetch_match_events_from_api(fixture_id: int):
    """Fetch match events from API-Football"""
    headers = {'x-apisports-key': API_FOOTBALL_KEY}
    
    print(f"\n[API-Football] Fetching events for fixture {fixture_id}...")
    
    # Get fixture details
    response = requests.get(f'{API_FOOTBALL_BASE_URL}/fixtures', headers=headers, params={'id': fixture_id})
    fixture_response = response.json()
    fixture_data = fixture_response['response'][0]
    
    # Get events
    response = requests.get(f'{API_FOOTBALL_BASE_URL}/fixtures/events', headers=headers, params={'fixture': fixture_id})
    events_response = response.json()
    events_data = events_response['response']
    
    print(f"  ✓ Found {len(events_data)} events")
    
    # Combine full API response for debugging
    full_api_response = {
        "fixture": fixture_response,
        "events": events_response
    }
    
    return fixture_data, events_data, full_api_response


def expand_clip_window(event):
    """10 second clips for all events with type-specific framing"""
    timestamp = event.get('video_timestamp_seconds')
    if not timestamp:
        return event
    
    event_type = event.get('event_type', 'other')
    
    # Goals get longer pre-roll to capture buildup
    if event_type in ['goal', 'penalty_goal', 'own_goal']:
        event['clip_start_sec'] = max(0, timestamp - 3)
        event['clip_end_sec'] = timestamp + 7
    # Dramatic moments and near-goals get standard 10s
    elif event_type in ['var_review', 'missed_penalty', 'penalty_awarded', 'foul']:
        event['clip_start_sec'] = max(0, timestamp - 2)
        event['clip_end_sec'] = timestamp + 8
    # Cards and substitutions get standard 10s
    elif event_type in ['card', 'substitution']:
        event['clip_start_sec'] = max(0, timestamp - 2)
        event['clip_end_sec'] = timestamp + 8
    # Fallback for unknown event types
    else:
        event['clip_start_sec'] = max(0, timestamp - 2)
        event['clip_end_sec'] = timestamp + 8
    
    return event


def retry_failed_events(video_file, failed_events, gemini_client, model_name):
    """Retry Gemini Vision for events it couldn't find — with API hints"""
    if not failed_events:
        return []
    
    print(f"\n[Re-grounding] Retrying {len(failed_events)} failed events with API hints...")
    retried = []
    
    for event in failed_events:
        player = event.get('player', 'Unknown')
        event_type = event.get('event_type', 'unknown')
        match_minute = event.get('match_minute', '?')
        team = event.get('team', 'Unknown')
        
        print(f"  [Re-grounding] Retrying: {player} {event_type} at {match_minute} min...")
        
        prompt = f"""Watch this football highlights video carefully.

I need you to find ONE specific moment in this video.

Known facts from official match data:
- Event: {event_type}
- Player: {player}
- Team: {team}
- Match minute: {match_minute}
- This event DEFINITELY happened in this match

Look for:
- Scoreboard showing around minute {match_minute}
- Player name "{player}" appearing on screen
- {team} players celebrating or reacting
- Commentary or crowd reaction consistent with a {event_type}

Return JSON only:
{{
  "player": "{player}",
  "event_type": "{event_type}",
  "team": "{team}",
  "match_minute": "{match_minute}",
  "video_timestamp_seconds": <seconds into this video where event occurs>,
  "clip_start_sec": <video_timestamp - 3>,
  "clip_end_sec": <video_timestamp + 7>,
  "found": true or false,
  "confidence": "high/medium/low",
  "detection_method": "re_grounded"
}}

If you still cannot find this event return found=false.
Return JSON only, no other text."""

        try:
            response = gemini_client.models.generate_content(
                model=model_name,
                contents=[video_file, prompt]
            )
            clean = response.text.replace("```json", "").replace("```", "").strip()
            result = json.loads(clean)
            result['detection_method'] = 're_grounded'
            
            # Apply clip window expansion
            result = expand_clip_window(result)
            
            retried.append(result)
            status = "✓ FOUND" if result.get('found') else "✗ STILL NOT FOUND"
            print(f"    {status} — confidence: {result.get('confidence')}")
        except Exception as e:
            print(f"    ✗ Error: {e}")
            event['detection_method'] = 're_grounded_failed'
            event['found'] = False
            retried.append(event)
    
    return retried


def self_consistency_check(mapped_events, api_events):
    """Cross-check Gemini results against API-Football ground truth"""
    print("\n[Self-Consistency Check]")
    issues = []
    
    # Check 1: Timestamp ordering — events should be in chronological order
    found_events = [e for e in mapped_events if e.get('found')]
    timestamps = [e.get('video_timestamp_seconds', 0) for e in found_events]
    
    for i in range(1, len(timestamps)):
        if timestamps[i] <= timestamps[i-1]:
            issues.append(f"Timestamp order issue: event {i} ({timestamps[i]}s) <= event {i-1} ({timestamps[i-1]}s)")
    
    # Check 2: Team name agreement between Gemini and API-Sports
    for gemini_event in mapped_events:
        if not gemini_event.get('found'):
            continue
        
        player = gemini_event.get('player')
        gemini_team = gemini_event.get('team', '').lower()
        
        # Find matching API event by player name
        for api_event in api_events:
            api_player = api_event.get('player', {}).get('name', '')
            if api_player == player:
                api_team = api_event.get('team', {}).get('name', '').lower()
                # Check if team names match (partial match allowed)
                if gemini_team and api_team and gemini_team not in api_team and api_team not in gemini_team:
                    issues.append(f"Team mismatch for {player}: Gemini='{gemini_team}', API='{api_team}'")
                break
    
    # Check 3: Found count summary
    total_events = len(mapped_events)
    found_count = len([e for e in mapped_events if e.get('found')])
    not_found_count = total_events - found_count
    
    print(f"  Events found: {found_count}/{total_events}")
    print(f"  Events not found: {not_found_count}/{total_events}")
    
    if issues:
        print(f"  ⚠ {len(issues)} consistency issues detected:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print(f"  ✓ All consistency checks passed")
    
    return issues


def map_events_to_video_timestamps(events, video_path: Path):
    """Use Gemini Vision to map match events to video timestamps"""
    print(f"\n[Gemini Vision] Mapping events to video timestamps...")
    
    if not video_path.exists():
        print(f"  ❌ Video not found: {video_path}")
        return None
    
    # Upload video
    print(f"  → Uploading video...")
    video_file = gemini_client.files.upload(file=str(video_path))
    
    # Wait for processing
    print(f"  → Processing", end="", flush=True)
    while video_file.state == "PROCESSING":
        print(".", end="", flush=True)
        time.sleep(2)
        video_file = gemini_client.files.get(name=video_file.name)
    print(f" ✓")
    
    # Prepare event list for Gemini - send ALL interesting events
    # Priority tiers: HIGH (goals, VAR), MEDIUM (cards, near misses), LOW (substitutions)
    known_events = []
    for event in events:
        event_type = None
        
        # Map event types based on API-Sports 'type' and 'detail' fields
        if event['type'] == 'Goal':
            if event.get('detail') == 'Missed Penalty':
                event_type = "missed_penalty"  # MEDIUM priority - near goal moment
            else:
                event_type = "goal"  # HIGH priority
        elif event['type'] == 'Card':
            event_type = "card"  # MEDIUM priority
        elif event['type'] == 'subst':
            event_type = "substitution"  # LOW priority
        elif event['type'] == 'Var':
            event_type = "var_review"  # HIGH priority - dramatic moment
        # Note: API-Sports doesn't track saves/woodwork hits as separate events
        # Those would need pure vision-based detection (unreliable with current Gemini)
        
        # Only send events we can map
        if event_type:
            known_events.append({
                "minute": str(event['time']['elapsed']),
                "event_type": event_type,
                "team": event['team']['name'],
                "player": event['player']['name']
            })
    
    # Create prompt
    prompt = f"""Watch this football highlights video carefully.

I know these events happened in the match:
{json.dumps(known_events, indent=2)}

For each event, find exactly where it appears in this highlights video and return the video timestamp in seconds.

Return JSON only in this exact format:
{{
  "mapped_events": [
    {{
      "player": "<player name>",
      "event_type": "<goal/card/substitution/missed_penalty/var_review>",
      "team": "<team>",
      "match_minute": "<minute from API>",
      "video_timestamp_seconds": <seconds into this video>,
      "clip_start_sec": <video_timestamp - 3 for goals, video_timestamp - 2 for others>,
      "clip_end_sec": <video_timestamp + 7 for goals, video_timestamp + 8 for others>,
      "found": true/false,
      "confidence": "high/medium/low"
    }}
  ]
}}

Note: 
- Goals need 10s clips (3 sec before, 7 sec after) to capture buildup and celebration
- Cards, substitutions, VAR reviews, and missed penalties need 10s clips (2 sec before, 8 sec after)
- For substitutions: look for player name on substitution graphic/board
- For VAR reviews: look for "VAR" graphic or referee checking monitor
- For missed penalties: look for penalty kick that doesn't score

If you cannot find an event in the video set found=false.
Return JSON only, no other text."""
    
    print(f"  → Asking Gemini to map {len(known_events)} events...")
    model_name = "gemini-2.5-pro"
    response = gemini_client.models.generate_content(
        model=model_name,
        contents=[video_file, prompt]
    )
    
    # Parse response - FIRST ATTEMPT
    first_attempt_events = []
    try:
        clean = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)
        first_attempt_events = result['mapped_events']
        
        # Post-process: Recalculate clip boundaries based on event type
        print(f"  → Recalculating clip boundaries based on event types...")
        first_attempt_events = [expand_clip_window(event) for event in first_attempt_events]
        
        # Mark detection method for first attempt
        for event in first_attempt_events:
            if 'detection_method' not in event:
                event['detection_method'] = 'first_attempt'
        
        found_count = len([e for e in first_attempt_events if e.get('found')])
        not_found_count = len(first_attempt_events) - found_count
        print(f"  ✓ First attempt: {found_count}/{len(first_attempt_events)} events found")
        
        # Step 2: RETRY FAILED EVENTS with re-grounding
        failed_events = [e for e in first_attempt_events if not e.get('found')]
        retried_events = []
        
        if failed_events:
            retried_events = retry_failed_events(
                video_file=video_file,
                failed_events=failed_events,
                gemini_client=gemini_client,
                model_name=model_name
            )
        
        # Step 3: MERGE results - replace failed events with retried versions
        final_mapped_events = []
        for event in first_attempt_events:
            if event.get('found'):
                final_mapped_events.append(event)
            else:
                # Find corresponding retried event
                player = event.get('player')
                retried = next((e for e in retried_events if e.get('player') == player), event)
                final_mapped_events.append(retried)
        
        # Step 4: SELF-CONSISTENCY CHECK
        consistency_issues = self_consistency_check(final_mapped_events, events)
        
        # Build enhanced result with metadata
        enhanced_result = {
            'mapped_events': final_mapped_events,
            'first_attempt': {
                'found': len([e for e in first_attempt_events if e.get('found')]),
                'not_found': len([e for e in first_attempt_events if not e.get('found')])
            },
            'after_regrounding': {
                'found': len([e for e in final_mapped_events if e.get('found')]),
                'not_found': len([e for e in final_mapped_events if not e.get('found')])
            },
            'consistency_issues': consistency_issues
        }
        
        final_found = enhanced_result['after_regrounding']['found']
        total = len(final_mapped_events)
        print(f"\n  ✓ Final result: {final_found}/{total} events mapped")
        
        return enhanced_result
        
    except Exception as e:
        print(f"  ❌ Failed to parse Gemini response: {e}")
        return None


def score_for_reel_a(event, preferred_team, preferred_players):
    """
    Calculate priority score for Reel A (personalized) based on preferred team/players.
    
    Args:
        event: Event dict with 'importance', 'team', 'players' fields
        preferred_team: User's preferred team name
        preferred_players: List of preferred player names
        
    Returns:
        Float score (higher = higher priority)
    """
    score = event.get('importance', 0.5)
    
    # Bonus for preferred team
    if event.get('team') == preferred_team:
        score += 0.3
    
    # Bonus for preferred player involvement
    for player in event.get('players', []):
        for pref in preferred_players:
            if pref.lower() in player.lower():
                score += 0.5
                break  # Only count once per player
    
    return score


def build_entity_registry(fixture_data, events_data):
    """Build entity registry from fixture and events"""
    registry = []
    
    # Add teams
    home_team = fixture_data['teams']['home']['name']
    away_team = fixture_data['teams']['away']['name']
    
    registry.append({
        "entity_id": f"team_{home_team.lower().replace(' ', '_')}",
        "entity_type": "team",
        "canonical_name": home_team,
        "aliases": [home_team],
        "team_id": home_team.lower().replace(' ', '_')
    })
    
    registry.append({
        "entity_id": f"team_{away_team.lower().replace(' ', '_')}",
        "entity_type": "team",
        "canonical_name": away_team,
        "aliases": [away_team, away_team.split()[-1]],
        "team_id": away_team.lower().replace(' ', '_')
    })
    
    # Add players from events
    players_seen = set()
    player_name_map = {}  # Track variations of same player (e.g., "P. Foden" vs "Phil Foden")
    
    for event in events_data:
        player_name = event['player']['name']
        if not player_name:
            continue
            
        # Normalize: check if this is a duplicate with abbreviated first name
        # e.g., "P. Foden" and "Phil Foden" should be same entity
        last_name = player_name.split()[-1] if ' ' in player_name else player_name
        
        # Check if we've seen this last name before
        existing_name = None
        for seen_name in players_seen:
            seen_last = seen_name.split()[-1] if ' ' in seen_name else seen_name
            if last_name == seen_last:
                # Same last name - check if one is abbreviated
                # Keep the longer (full) version
                if len(player_name) > len(seen_name):
                    # New name is fuller, replace old one
                    players_seen.discard(seen_name)
                    player_name_map[player_name] = player_name
                    existing_name = None  # Will add the new fuller name
                    break
                else:
                    # Existing name is fuller or same, skip this one
                    existing_name = seen_name
                    player_name_map[player_name] = seen_name  # Map abbreviated to full
                    break
        
        if existing_name:
            continue  # Skip duplicate
            
        players_seen.add(player_name)
        team_name = event['team']['name']
        
        registry.append({
            "entity_id": f"player_{player_name.lower().replace(' ', '_').replace('.', '')}",
            "entity_type": "player",
            "canonical_name": player_name,
            "aliases": [player_name, player_name.split()[-1]],
            "team_id": team_name.lower().replace(' ', '_')
        })
    
    return registry


def build_score_progression(fixture_data, events_data):
    """Build score progression timeline"""
    progression = [{"time": "0:00", "score": "0-0", "event": "kickoff"}]
    
    home_score = 0
    away_score = 0
    home_team = fixture_data['teams']['home']['name']
    
    for event in events_data:
        if event['type'] == 'Goal' and event['detail'] != 'Missed Penalty':
            player = event['player']['name']
            team = event['team']['name']
            minute = event['time']['elapsed']
            
            # Update score
            if team == home_team:
                home_score += 1
            else:
                away_score += 1
            
            progression.append({
                "time": f"{minute}:00",
                "score": f"{home_score}-{away_score}",
                "scorer": player,
                "team": team,
                "event": "goal"
            })
    
    return progression


def generate_dl_handoff(fixture_data, events_data, mapped_events, entity_registry, score_progression, output_path: Path, youtube_video_id=None):
    """Generate approach_b_dl_handoff.json"""
    
    # Extract match context
    match_context = {
        "match_id": str(fixture_data['fixture']['id']),
        "home_team": fixture_data['teams']['home']['name'],
        "away_team": fixture_data['teams']['away']['name'],
        "competition": fixture_data['league']['name'],
        "season": f"{fixture_data['league']['season']}-{fixture_data['league']['season']+1}",
        "date": fixture_data['fixture']['date'][:10],
        "venue": fixture_data['fixture']['venue']['name'],
        "final_score": f"{fixture_data['goals']['home']}-{fixture_data['goals']['away']}"
    }
    
    # Add video_id if youtube_video_id provided
    if youtube_video_id:
        match_context["video_id"] = f"youtube_{youtube_video_id}"
    
    # Build events array
    events = []
    timestamp_map = {(e['player'], e['match_minute']): e for e in mapped_events} if mapped_events else {}
    
    for idx, event in enumerate(events_data, 1):
        player_name = event['player']['name']
        minute = str(event['time']['elapsed'])
        
        # Get timestamp from Gemini mapping
        mapped = timestamp_map.get((player_name, minute))
        video_timestamp = mapped['video_timestamp_seconds'] if mapped and mapped.get('found') else None
        clip_start = mapped['clip_start_sec'] if mapped and mapped.get('found') else None
        clip_end = mapped['clip_end_sec'] if mapped and mapped.get('found') else None
        
        # Map event type and assign importance
        # Priority system:
        # - HIGH (0.9-0.95): Goals, VAR reviews (dramatic/decisive moments)
        # - MEDIUM (0.6-0.7): Cards, missed penalties (tension/excitement)
        # - LOW (0.5): Substitutions (routine changes)
        event_type = "unknown"
        importance = 0.5
        
        if event['type'] == 'Goal':
            if event.get('detail') == 'Missed Penalty':
                event_type = "missed_penalty"
                importance = 0.7  # MEDIUM-HIGH: near goal moment
            elif event['detail'] == 'Own Goal':
                event_type = "own_goal"
                importance = 0.95  # HIGH: dramatic
            elif event['detail'] == 'Penalty':
                event_type = "penalty_goal"
                importance = 0.95  # HIGH: decisive
            else:
                event_type = "goal"
                importance = 0.95  # HIGH: most important
        elif event['type'] == 'Card':
            event_type = "card"
            importance = 0.6  # MEDIUM: tension
        elif event['type'] == 'subst':
            event_type = "substitution"
            importance = 0.5  # LOW: routine
        elif event['type'] == 'Var':
            event_type = "var_review"
            importance = 0.9  # HIGH: dramatic/controversial
        
        # Get score after event
        score_after = None
        for sp in score_progression:
            if sp.get('time') == f"{minute}:00" and sp.get('scorer') == player_name:
                score_after = sp['score']
                break
        
        # Build event dict
        event_dict = {
            "clip_id": f"segment_{idx:03d}",
            "time": f"{minute}:00",
            "time_seconds": int(minute) * 60.0,
            "event_type": event_type,
            "importance": importance,
            "confidence": 0.99,
            "team": event['team']['name'],
            "players": [player_name] + ([event['assist']['name']] if event.get('assist', {}).get('name') else []),
            "score_after_event": score_after,
            "clip_start_sec": clip_start,
            "clip_end_sec": clip_end,
            "ocr_text": [player_name, f"{minute}:00"],
            "match_phase": "first_half" if int(minute) <= 45 else "second_half",
            "context": {
                "previous_event": None,
                "next_event": None,
                "narrative": f"{player_name} — {event['detail'].replace('Normal Goal', 'Goal')} for {event['team']['name']} at {minute} minutes."
            }
        }
        
        # For goals/penalties, add explicit scorer/assist fields to avoid LLM confusion
        if event_type in ['goal', 'penalty_goal']:
            event_dict['scorer'] = player_name
            if event.get('assist', {}).get('name'):
                event_dict['assist'] = event['assist']['name']
        
        # ONLY append events with valid video timestamps (skip cards/subs not found by Vision)
        if clip_start is not None:
            events.append(event_dict)
        else:
            print(f"⚠ Skipping {event_type} ({player_name} {minute}') - no video timestamp")
    
    # Build final JSON
    dl_handoff = {
        "match_context": match_context,
        "entity_registry": entity_registry,
        "score_progression": score_progression,
        "events": events
    }
    
    # Save to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(dl_handoff, f, indent=2)
    
    print(f"\n✓ Generated: {output_path}")
    return dl_handoff


def generate_highlight_candidates(dl_handoff, output_path: Path):
    """Generate approach_b_highlight_candidates.json in D15 format (flat array)"""
    
    highlight_candidates = []
    importance_rank = 1
    
    for event in dl_handoff['events']:
        if event['event_type'] in ['goal', 'own_goal', 'penalty_goal']:
            # Extract match minute from time string (e.g., "2:00" -> 2)
            match_minute = int(event['time'].split(':')[0])
            
            highlight_candidates.append({
                "segment_id": event['clip_id'],
                "time_range": {
                    "start": event.get('clip_start_sec'),
                    "end": event.get('clip_end_sec')
                },
                "predicted_event_type": event['event_type'],
                "confidence": event['confidence'],
                "importance_score": event['importance'],
                "importance_rank": importance_rank,
                "team": event['team'],
                "players": event['players'],
                "score_after_event": event.get('score_after_event', '0-0'),
                "score_context": {
                    "home_team": dl_handoff['match_context']['home_team'],
                    "away_team": dl_handoff['match_context']['away_team'],
                    "home_score": int(event.get('score_after_event', '0-0').split('-')[0]) if event.get('score_after_event') else 0,
                    "away_score": int(event.get('score_after_event', '0-0').split('-')[1]) if event.get('score_after_event') else 0,
                    "score_change_detected": True
                },
                "match_phase": event['match_phase'],
                "match_time_display": event['time'],
                "ocr_text": event.get('ocr_text', []),
                
                # ===================================================================
                # WARNING: LEGACY FIELDS BELOW - NOT USED BY PIPELINE
                # ===================================================================
                # These fields were added for backward compatibility with old mock
                # data format. They are NOT used by any agent or pipeline code.
                # TODO: Remove in future refactor (after validating no dependencies)
                # Fields to remove: modality_scores, feature_vector, top_labels,
                #                   supporting_*_event_ids, rationale, 
                #                   heuristic_importance_score, ranking_model,
                #                   importance_reasons, judgment_criteria,
                #                   prompt_template, analysis_prompt,
                #                   dynamic_adjustments, about_summary,
                #                   context_tags, emotion_tags
                # ===================================================================
                "modality_scores": {
                    "audio": 0.95,
                    "visual": 0.94,
                    "context": 0.92
                },
                "feature_vector": {
                    "audio_peak": 0.95,
                    "audio_density": 1.0,
                    "audio_excitement": 0.92,
                    "audio_whistle": 0.85,
                    "audio_applause": 0.0,
                    "audio_crowd": 0.96,
                    "audio_commentary": 1.0,
                    "audio_score_update": 1.0,
                    "audio_celebration": 0.88,
                    "audio_foul_or_penalty": 0.85 if event['event_type'] == 'penalty_goal' else 0.0,
                    "audio_stoppage_review": 0.0,
                    "audio_substitution": 0.0,
                    "audio_injury_pause": 0.0,
                    "audio_high_tension": 0.80,
                    "visual_motion": 0.85,
                    "visual_replay": 0.0,
                    "visual_ocr": 1.0,
                    "visual_face": 1.0,
                    "visual_face_count": 6.0,
                    "visual_positive_emotion": 0.91,
                    "visual_negative_emotion": 0.05,
                    "visual_surprise": 0.72,
                    "context_scoreboard_visible": 1.0,
                    "context_crowd_reaction": 0.95,
                    "context_celebration": 0.90,
                    "context_disappointment": 0.0,
                    "context_stoppage_review": 0.0,
                    "context_bench_reaction": 0.6,
                    "context_highlight_package": 0.0,
                    "context_substitution": 0.0,
                    "context_injury": 0.0,
                    "context_high_tension": 0.75
                },
                "top_labels": [  # LEGACY - NOT USED
                    {"label": event['event_type'], "score": 0.97},
                    {"label": "celebration", "score": 0.88},
                    {"label": "crowd_peak", "score": 0.72}
                ],
                "context_tags": ["goal", "score_change", "crowd_eruption"],  # LEGACY - NOT USED
                "emotion_tags": ["excitement", "celebration"],  # LEGACY - NOT USED
                "domain_inference": "soccer_broadcast",
                "domain_confidence": 0.96,
                "about_summary": event['context']['narrative'],  # LEGACY - NOT USED
                "judgment_criteria": [  # LEGACY - NOT USED
                    "Goal event from API-Football",
                    "Video timestamp confirmed by Gemini Vision",
                    "Score progression tracked"
                ],
                "context_summary": event['context']['narrative'],
                "prompt_template": "default_soccer_goal",  # LEGACY - NOT USED
                "analysis_prompt": f"Analyze goal scored by {event['players'][0]} at {event['time']}",  # LEGACY - NOT USED
                "dynamic_adjustments": {  # LEGACY - NOT USED
                    "adjust_for_user_team": True,
                    "adjust_for_player_mention": True,
                    "adjust_for_score_significance": True
                },
                "supporting_audio_event_ids": [],  # LEGACY - NOT USED
                "supporting_video_event_ids": [],  # LEGACY - NOT USED
                "rationale": [  # LEGACY - NOT USED
                    f"Goal scored by {event['players'][0]}",
                    f"Match minute: {match_minute}",
                    f"Score after: {event.get('score_after_event', 'N/A')}"
                ],
                "heuristic_importance_score": event['importance'],  # LEGACY - NOT USED
                "ranking_model": "api_football_gemini_vision",  # LEGACY - NOT USED
                "importance_reasons": [  # LEGACY - NOT USED
                    {"reason": "Goal event", "weight": 0.95},
                    {"reason": "Score change", "weight": 0.90}
                ]
            })
            importance_rank += 1
    
    # Save to file (flat array format)
    with open(output_path, 'w') as f:
        json.dump(highlight_candidates, f, indent=2)
    
    print(f"✓ Generated: {output_path}")
    return highlight_candidates


def main():
    parser = argparse.ArgumentParser(description='Approach B Ingestor - Fully Autonomous Match Data Generation')
    parser.add_argument('--match', required=True, help='Match folder name (e.g., arsenal_5_1_man_city_2025_02_02)')
    parser.add_argument('--video', required=True, help='Video filename in Source_Videos/ (e.g., arsenal_5_1_man_city.mp4)')
    parser.add_argument('--fixture-id', type=int, required=False, help='API-Football fixture ID (optional, will search if not provided)')
    parser.add_argument('--youtube-id', required=False, help='YouTube video ID (e.g., f3POqcfPJZ8)')
    
    args = parser.parse_args()
    
    # Start timing
    ingestor_start_time = time.time()
    
    print("=" * 60)
    print("APPROACH B INGESTOR — Fully Autonomous")
    print("=" * 60)
    
    # Paths
    match_folder = MOCK_DATA_DIR / args.match
    video_path = SOURCE_VIDEOS_DIR / args.video
    dl_handoff_path = match_folder / "approach_b_dl_handoff.json"
    highlight_candidates_path = match_folder / "approach_b_highlight_candidates.json"
    
    # If fixture ID not provided, we need to search - for now require it
    if not args.fixture_id:
        print("\n❌ Error: --fixture-id is required for now")
        print("   Example: --fixture-id 1208254")
        sys.exit(1)
    
    # Step 1: Fetch match events from API
    step1_start = time.time()
    fixture_data, events_data, full_api_response = fetch_match_events_from_api(args.fixture_id)
    print(f"  ✓ API fetch: {round(time.time() - step1_start, 2)}s")
    
    # Save raw API response for debugging
    api_debug_path = BACKEND_DIR / "Outputs" / f"api_sports_{args.match}_full.json"
    api_debug_path.parent.mkdir(parents=True, exist_ok=True)
    with open(api_debug_path, 'w', encoding='utf-8') as f:
        json.dump(full_api_response, f, indent=2, ensure_ascii=False)
    print(f"  ✓ API response saved to: {api_debug_path}")
    
    # Step 2: Map events to video timestamps
    step2_start = time.time()
    gemini_result = map_events_to_video_timestamps(events_data, video_path)
    print(f"  ✓ Gemini Vision mapping: {round(time.time() - step2_start, 2)}s")
    mapped_events = gemini_result['mapped_events'] if gemini_result else None
    
    # Save Gemini raw mapping for debugging
    if gemini_result:
        gemini_debug_path = Path(__file__).parent.parent / "Outputs" / args.match / "gemini_timestamp_mapping.json"
        gemini_debug_path.parent.mkdir(parents=True, exist_ok=True)
        with open(gemini_debug_path, 'w', encoding='utf-8') as f:
            json.dump(gemini_result, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Gemini mapping saved to: {gemini_debug_path}")
        
        # Save extraction report with detailed metadata
        extraction_report = {
            "match": args.match,
            "timestamp": datetime.now().isoformat(),
            "total_events": len(mapped_events) if mapped_events else 0,
            "first_attempt": gemini_result.get('first_attempt', {}),
            "after_regrounding": gemini_result.get('after_regrounding', {}),
            "consistency_issues": gemini_result.get('consistency_issues', []),
            "mapped_events": mapped_events
        }
        
        report_path = Path(__file__).parent.parent / "Outputs" / args.match / "extraction_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(extraction_report, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Extraction report saved to: {report_path}")
    
    # Step 3: Build entity registry
    entity_registry = build_entity_registry(fixture_data, events_data)
    print(f"\n[Entity Registry] Built {len(entity_registry)} entities")
    
    # Step 4: Build score progression
    score_progression = build_score_progression(fixture_data, events_data)
    print(f"[Score Progression] Tracked {len(score_progression)-1} goals")
    
    # Step 5: Generate approach_b_dl_handoff.json
    dl_handoff = generate_dl_handoff(
        fixture_data, events_data, mapped_events, 
        entity_registry, score_progression, dl_handoff_path,
        youtube_video_id=args.youtube_id
    )
    
    # Step 6: Generate approach_b_highlight_candidates.json
    highlight_candidates = generate_highlight_candidates(dl_handoff, highlight_candidates_path)
    
    # Record and save total timing
    ingestor_total_time = round(time.time() - ingestor_start_time, 2)
    print(f"\n[Ingestor] Total time: {ingestor_total_time:.2f}s")
    
    # Save timing to outputs
    timing_path = BACKEND_DIR / "Outputs" / args.match / "ingestor_timing.json"
    timing_path.parent.mkdir(parents=True, exist_ok=True)
    with open(timing_path, 'w') as f:
        json.dump({
            "match": args.match,
            "timestamp": datetime.now().isoformat(),
            "total_seconds": ingestor_total_time,
        }, f, indent=2)
    print(f"✓ Timing saved to: {timing_path}")
    
    print("\n" + "=" * 60)
    print("✅ APPROACH B INGESTOR COMPLETE")
    print("=" * 60)
    print(f"\nGenerated files in: {match_folder}/")
    print(f"  - approach_b_dl_handoff.json ({len(dl_handoff['events'])} events)")
    print(f"  - approach_b_highlight_candidates.json ({len(highlight_candidates)} highlights)")
    print(f"\nNext step: Update config.py ACTIVE_MATCH = '{args.match}'")


if __name__ == "__main__":
    main()
