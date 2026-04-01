"""
Baseline Keyword Matching Approach: No LLM

Simple keyword-based filtering baseline - no LLM, just string matching.
Selects events based on keyword overlap with user preference.
"""

import sys
import json
from pathlib import Path

# Setup paths for imports
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))


def load_mock_data():
    """Load D17 handoff mock data."""
    mock_data_path = backend_dir / "Mock_Data" / "dl_handoff_mock.json"
    
    with open(mock_data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data


def extract_keywords(user_preference: str) -> list:
    """
    Extract keywords from user preference string.
    
    Args:
        user_preference: User's preference string
        
    Returns:
        List of lowercase keywords (words longer than 3 characters)
    """
    # Split by spaces and punctuation
    words = user_preference.replace(',', ' ').replace('.', ' ').split()
    
    # Filter: lowercase, longer than 3 characters
    keywords = [word.lower() for word in words if len(word) > 3]
    
    return keywords


def score_event(event: dict, keywords: list) -> int:
    """
    Score event based on keyword matches.
    
    Args:
        event: Event dict from D17
        keywords: List of keywords to match
        
    Returns:
        Number of keyword matches found
    """
    score = 0
    
    # Get searchable text from event (lowercase)
    team = event['team'].lower() if event['team'] else ""
    players = [p.lower() for p in event['players']] if event['players'] else []
    
    # Check each keyword
    for keyword in keywords:
        # Check team match
        if keyword in team:
            score += 1
        
        # Check player matches
        for player in players:
            if keyword in player:
                score += 1
    
    return score


def filter_events_by_keywords(events: list, user_preference: str, top_k: int = 5) -> list:
    """
    Filter and rank events by keyword matching.
    
    Args:
        events: List of event dicts
        user_preference: User's preference string
        top_k: Number of top events to return
        
    Returns:
        List of scored events with match_score field
    """
    # Extract keywords
    keywords = extract_keywords(user_preference)
    
    print(f"Extracted keywords: {keywords}")
    
    # Score each event
    scored_events = []
    for event in events:
        match_score = score_event(event, keywords)
        
        scored_event = {
            "clip_id": event['clip_id'],
            "event_type": event['event_type'],
            "team": event['team'],
            "players": event['players'],
            "time": event['time'],
            "score_after_event": event['score_after_event'],
            "importance": event['importance'],
            "match_score": match_score,
        }
        
        scored_events.append(scored_event)
    
    # Sort by match_score (descending), then importance (descending)
    scored_events.sort(key=lambda x: (x['match_score'], x['importance']), reverse=True)
    
    # Return top K
    return scored_events[:top_k]


def run_baseline(user_preference: str, top_k: int = 5) -> dict:
    """
    Run the baseline keyword matching approach.
    
    Args:
        user_preference: User's preference string
        top_k: Number of top events to return
        
    Returns:
        Dict with filtered events and metadata
    """
    
    print("=" * 80)
    print("BASELINE: Keyword Matching Approach (No LLM)")
    print("=" * 80)
    print(f"\nUser preference: {user_preference}")
    print(f"Top K: {top_k}")
    
    # Load data
    print("\nLoading mock data...")
    data = load_mock_data()
    match_context = data['match_context']
    events = data['events']
    
    print(f"✓ Loaded {len(events)} events")
    print(f"  Match: {match_context['home_team']} vs {match_context['away_team']}")
    
    # Filter by keywords
    print("\nFiltering events by keyword matching...")
    filtered_events = filter_events_by_keywords(events, user_preference, top_k)
    
    print(f"✓ Selected {len(filtered_events)} events")
    
    # Display results
    print("\n" + "-" * 80)
    print("Top Events by Keyword Match:")
    print("-" * 80)
    for i, event in enumerate(filtered_events, 1):
        print(f"\n{i}. {event['event_type'].upper()} - {event['team']}")
        print(f"   Players: {', '.join(event['players']) if event['players'] else 'N/A'}")
        print(f"   Time: {event['time']} | Score: {event['score_after_event']}")
        print(f"   Match score: {event['match_score']} | Importance: {event['importance']:.2f}")
    print("-" * 80)
    
    result = {
        "user_preference": user_preference,
        "total_events": len(events),
        "selected_events": len(filtered_events),
        "keywords": extract_keywords(user_preference),
        "events": filtered_events,
        "status": "success",
    }
    
    print(f"\n✓ Baseline complete: {len(filtered_events)} events selected")
    
    return result


if __name__ == "__main__":
    # Test with Arsenal fan preference
    preference = "I am an Arsenal fan and I love watching Saka play"
    
    result = run_baseline(preference, top_k=5)
    
    # Save results
    output_path = backend_dir / "baselines" / "baseline_keyword_results.json"
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Results saved to: {output_path}")
    print("=" * 80)
