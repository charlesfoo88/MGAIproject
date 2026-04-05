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
    response = gemini_client.models.generate_content(
        model="gemini-2.5-pro",
        contents=[video_file, prompt]
    )
    
    # Parse response
    try:
        clean = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)
        mapped_events = result['mapped_events']
        
        # Post-process: Recalculate clip boundaries based on event type
        print(f"  → Recalculating clip boundaries based on event types...")
        mapped_events = [expand_clip_window(event) for event in mapped_events]
        
        # Update result with expanded events
        result['mapped_events'] = mapped_events
        
        print(f"  ✓ Mapped {len(mapped_events)} events")
        return result
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
    for event in events_data:
        player_name = event['player']['name']
        if player_name and player_name not in players_seen:
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
        
        events.append({
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
        })
    
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
    fixture_data, events_data, full_api_response = fetch_match_events_from_api(args.fixture_id)
    
    # Save raw API response for debugging
    api_debug_path = BACKEND_DIR / "Outputs" / f"api_sports_{args.match}_full.json"
    api_debug_path.parent.mkdir(parents=True, exist_ok=True)
    with open(api_debug_path, 'w', encoding='utf-8') as f:
        json.dump(full_api_response, f, indent=2, ensure_ascii=False)
    print(f"  ✓ API response saved to: {api_debug_path}")
    
    # Step 2: Map events to video timestamps
    gemini_result = map_events_to_video_timestamps(events_data, video_path)
    mapped_events = gemini_result['mapped_events'] if gemini_result else None
    
    # Save Gemini raw mapping for debugging
    if gemini_result:
        gemini_debug_path = Path(__file__).parent.parent / "Outputs" / args.match / "gemini_timestamp_mapping.json"
        gemini_debug_path.parent.mkdir(parents=True, exist_ok=True)
        with open(gemini_debug_path, 'w', encoding='utf-8') as f:
            json.dump(gemini_result, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Gemini mapping saved to: {gemini_debug_path}")
    
    # Step 3: Build entity registry
    entity_registry = build_entity_registry(fixture_data, events_data)
    print(f"\n[Entity Registry] Built {len(entity_registry)} entities")
    
    # Step 4: Build score progression
    score_progression = build_score_progression(fixture_data, events_data)
    print(f"[Score Progression] Tracked {len(score_progression)-1} goals")
    
    # Step 5: Generate dl_handoff.json
    dl_handoff = generate_dl_handoff(
        fixture_data, events_data, mapped_events, 
        entity_registry, score_progression, dl_handoff_path,
        youtube_video_id=args.youtube_id
    )
    
    # Step 6: Generate highlight_candidates.json
    highlight_candidates = generate_highlight_candidates(dl_handoff, highlight_candidates_path)
    
    print("\n" + "=" * 60)
    print("✅ APPROACH B INGESTOR COMPLETE")
    print("=" * 60)
    print(f"\nGenerated files in: {match_folder}/")
    print(f"  - approach_b_dl_handoff.json ({len(dl_handoff['events'])} events)")
    print(f"  - approach_b_highlight_candidates.json ({len(highlight_candidates)} highlights)")
    print(f"\nNext step: Update config.py ACTIVE_MATCH = '{args.match}'")


if __name__ == "__main__":
    main()
