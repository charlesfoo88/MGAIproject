"""
Baseline Non-Agentic Approach: Single Prompt

Simple baseline for comparison - no agents, no RAG, no hallucination checking.
Uses one LLM call to generate all captions at once.
"""

import sys
import json
import time
from pathlib import Path

# Setup paths for imports
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from config import GROQ_API_KEY, GROQ_MODEL, D17_FILE_PATH, ACTIVE_MATCH

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    print("Warning: groq package not installed")
    GROQ_AVAILABLE = False


def load_mock_data():
    """Load D17 handoff data from active match."""
    with open(D17_FILE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data


def build_single_prompt(match_context: dict, events: list, user_preference: str) -> str:
    """
    Build a single comprehensive prompt with all events.
    
    Args:
        match_context: Match metadata (home_team, away_team, etc.)
        events: List of event dicts from D17
        user_preference: User's preference string
        
    Returns:
        Complete prompt string
    """
    
    prompt = f"""You are a sports highlight caption generator.

Match Information:
- Home Team: {match_context['home_team']}
- Away Team: {match_context['away_team']}
- Competition: {match_context['competition']}
- Venue: {match_context['venue']}

User Preference: {user_preference}

Events to caption ({len(events)} total):

"""
    
    # Add each event
    for i, event in enumerate(events, 1):
        prompt += f"""Event {i}:
- Type: {event['event_type']}
- Team: {event['team']}
- Players: {', '.join(event['players']) if event['players'] else 'N/A'}
- Time: {event['time']}
- Score after: {event['score_after_event']}
- Narrative: {event['context']['narrative']}

"""
    
    prompt += f"""Task: Generate a personalized highlight caption for EACH of the {len(events)} events above.

Requirements:
- Create ONE caption per event (exactly {len(events)} captions total)
- Tailor captions to the user's preference when relevant
- Keep captions engaging and descriptive (2-3 sentences each)
- Reference specific players, teams, and actions from the event data
- Maintain factual accuracy

Output format:
Caption 1: [your caption for event 1]
Caption 2: [your caption for event 2]
...
Caption {len(events)}: [your caption for event {len(events)}]

Generate all {len(events)} captions now:"""
    
    return prompt


def call_groq_api(prompt: str) -> dict:
    """
    Call Groq API with the prompt.
    
    Args:
        prompt: Complete prompt string
        
    Returns:
        Dict with response text and metadata
    """
    if not GROQ_AVAILABLE:
        raise RuntimeError("Groq package not installed")
    
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set")
    
    client = Groq(api_key=GROQ_API_KEY)
    
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
        max_tokens=2000,
    )
    
    return {
        "text": response.choices[0].message.content,
        "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') else None,
        "prompt_tokens": response.usage.prompt_tokens if hasattr(response, 'usage') else None,
        "completion_tokens": response.usage.completion_tokens if hasattr(response, 'usage') else None,
    }


def parse_captions(response_text: str, expected_count: int) -> list:
    """
    Parse individual captions from LLM response.
    
    Args:
        response_text: Raw LLM response
        expected_count: Number of captions expected
        
    Returns:
        List of caption strings
    """
    captions = []
    
    # Split by lines and look for "Caption N:" pattern
    lines = response_text.strip().split('\n')
    
    current_caption = None
    for line in lines:
        line = line.strip()
        
        # Check if line starts with "Caption N:"
        if line.startswith("Caption ") and ":" in line:
            # Save previous caption if exists
            if current_caption is not None:
                captions.append(current_caption.strip())
            
            # Start new caption (text after the colon)
            parts = line.split(":", 1)
            if len(parts) == 2:
                current_caption = parts[1].strip()
            else:
                current_caption = ""
        elif current_caption is not None and line:
            # Continue current caption (multi-line)
            current_caption += " " + line
    
    # Don't forget the last caption
    if current_caption is not None:
        captions.append(current_caption.strip())
    
    # Validate count
    if len(captions) != expected_count:
        print(f"Warning: Expected {expected_count} captions, got {len(captions)}")
    
    return captions


def run_baseline(user_preference: str) -> dict:
    """
    Run the baseline single-prompt approach.
    
    Args:
        user_preference: User's preference string
        
    Returns:
        Dict with captions, timing, and metadata
    """
    
    print("=" * 80)
    print("BASELINE: Single Prompt Non-Agentic Approach")
    print("=" * 80)
    print(f"\nUser preference: {user_preference}")
    print("\nLoading mock data...")
    
    # Load data
    data = load_mock_data()
    match_context = data['match_context']
    events = data['events']
    
    print(f"✓ Loaded {len(events)} events")
    print(f"  Match: {match_context['home_team']} vs {match_context['away_team']}")
    
    # Build prompt
    print("\nBuilding single prompt...")
    prompt = build_single_prompt(match_context, events, user_preference)
    print(f"✓ Prompt built ({len(prompt)} characters)")
    
    # Call API
    print("\nCalling Groq API (single call)...")
    start_time = time.time()
    
    try:
        response = call_groq_api(prompt)
        end_time = time.time()
        time_taken = end_time - start_time
        
        print(f"✓ API call completed in {time_taken:.2f}s")
        if response['tokens_used']:
            print(f"  Tokens used: {response['tokens_used']} (prompt: {response['prompt_tokens']}, completion: {response['completion_tokens']})")
        
        # Parse captions
        print("\nParsing captions...")
        captions = parse_captions(response['text'], len(events))
        print(f"✓ Extracted {len(captions)} captions")
        
        # Display captions
        print("\n" + "-" * 80)
        print("Generated Captions:")
        print("-" * 80)
        for i, caption in enumerate(captions, 1):
            print(f"\n{i}. {caption}")
        print("-" * 80)
        
        result = {
            "user_preference": user_preference,
            "event_count": len(events),
            "captions": captions,
            "time_taken": round(time_taken, 2),
            "tokens_used": response['tokens_used'],
            "prompt_tokens": response['prompt_tokens'],
            "completion_tokens": response['completion_tokens'],
            "status": "success",
        }
        
        print(f"\n✓ Baseline complete: {len(captions)} captions in {time_taken:.2f}s")
        
        return result
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "user_preference": user_preference,
            "event_count": len(events),
            "captions": [],
            "time_taken": 0.0,
            "tokens_used": None,
            "status": "error",
            "error": str(e),
        }


if __name__ == "__main__":
    # Test with Arsenal fan preference
    preference = "I am an Arsenal fan and I love watching Saka play"
    
    result = run_baseline(preference)
    
    # Save results
    output_path = backend_dir / "Outputs" / ACTIVE_MATCH / "baseline_single_prompt_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Results saved to: {output_path}")
    print("=" * 80)
