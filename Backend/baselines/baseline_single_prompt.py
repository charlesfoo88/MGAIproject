"""
Baseline 1: Single Prompt Non-Agentic Approach

Minimal baseline for comparison against the full agentic pipeline.
Same inputs, same LLM, same clip selection, same caption constraints.
No RAG, no disagreement, no hallucination checking, no retry.

Usage:
    python Backend/baseline_single_prompt.py
"""

import sys
import json
import time
from pathlib import Path

# Setup paths for imports
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from config import GROQ_API_KEY, GROQ_MODEL, D17_FILE_PATH, ACTIVE_MATCH, OUTPUT_PATH
from Tools.embedding_tool import encode, cosine_similarity

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    print("Warning: groq package not installed")
    GROQ_AVAILABLE = False

MATCH_NAME = "arsenal_5_1_man_city_2025_02_02"


def load_eval_preferences() -> list:
    """Load evaluation preferences from evaluation_config.json, 
    or generate them from dl_handoff.json if not found."""
    config_path = OUTPUT_PATH / ACTIVE_MATCH / "evaluation_config.json"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        prefs = (config["auto_generated"]["disagreement_preferences"] + 
                 config["user_defined"]["disagreement_preferences"])
        print(f"Loaded {len(prefs)} preferences from evaluation_config.json")
        return prefs
    else:
        raise FileNotFoundError(f"evaluation_config.json not found at {config_path}. Run evaluate.py --full first.")


def load_handoff_data() -> dict:
    """Load D17 handoff data for active match."""
    with open(D17_FILE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def select_clips(events: list, max_clips: int = 6) -> list:
    """
    Select top clips by importance — same strategy as agentic pipeline.
    Importance >= 0.5 threshold, capped at max_clips.
    """
    filtered = [e for e in events if e.get('importance', 0) >= 0.5]
    sorted_events = sorted(filtered, key=lambda e: e.get('importance', 0), reverse=True)
    selected = sorted_events[:max_clips]
    print(f"  Clip selection: {len(events)} total -> {len(filtered)} above threshold -> {len(selected)} selected")
    return selected


def build_prompt(match_context: dict, events: list, user_preference: str) -> str:
    """
    Build single prompt with all event data and user preference.
    No RAG context, no entity enrichment — raw event data only.
    """
    prompt = f"""You are a sports highlight caption generator.

Match: {match_context['home_team']} vs {match_context['away_team']}
Competition: {match_context['competition']}
Venue: {match_context['venue']}
Final Score: {match_context['final_score']}

User Preference: {user_preference}

Events to caption ({len(events)} total):

"""
    for i, event in enumerate(events, 1):
        prompt += f"""Event {i}:
- Type: {event['event_type']}
- Team: {event['team']}
- Players: {', '.join(event['players']) if event['players'] else 'N/A'}
- Time: {event['time']}
- Score after: {event.get('score_after_event', 'N/A')}
- Narrative: {event['context']['narrative']}

"""

    prompt += f"""Task: Generate ONE personalised highlight caption per event.

Requirements:
1. Write EXACTLY 10-20 WORDS per caption
2. Tailor tone to the user preference
3. Reference specific players and actions
4. Maintain factual accuracy — only mention confirmed players and teams

Output format:
Caption 1: [caption]
Caption 2: [caption]
...
Caption {len(events)}: [caption]

Generate all {len(events)} captions now:"""

    return prompt


def call_groq(prompt: str) -> dict:
    """Single Groq API call — no retry, no hallucination check."""
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=800,
    )
    return {
        "text": response.choices[0].message.content,
        "tokens_used": response.usage.total_tokens,
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
    }


def parse_captions(response_text: str, expected_count: int) -> list:
    """Parse Caption N: format from LLM response."""
    captions = []
    current_caption = None

    for line in response_text.strip().split('\n'):
        line = line.strip()
        if line.startswith("Caption ") and ":" in line:
            if current_caption is not None:
                captions.append(current_caption.strip())
            parts = line.split(":", 1)
            current_caption = parts[1].strip() if len(parts) == 2 else ""
        elif current_caption is not None and line:
            current_caption += " " + line

    if current_caption is not None:
        captions.append(current_caption.strip())

    if len(captions) != expected_count:
        print(f"  Warning: Expected {expected_count} captions, got {len(captions)}")

    return captions


def compute_alignment_score(captions: list, user_preference: str) -> float:
    """
    Compute mean cosine similarity between captions and user preference.
    Same method as agentic pipeline (Sentence Transformers all-MiniLM-L6-v2).
    """
    if not captions:
        return 0.0
    pref_embedding = encode(user_preference)
    scores = []
    for caption in captions:
        caption_embedding = encode(caption)
        score = cosine_similarity(caption_embedding, pref_embedding)
        scores.append(score)
    return round(sum(scores) / len(scores), 3)


def run_baseline_single_prompt():
    """Run baseline for all 5 test preferences and save results."""

    print("=" * 80)
    print("BASELINE 1: SINGLE PROMPT")
    print("=" * 80)
    print(f"Match: {MATCH_NAME}")
    
    # Load preferences dynamically
    preferences = load_eval_preferences()
    
    print(f"Preferences: {len(preferences)}")
    print(f"Model: {GROQ_MODEL}")
    print(f"No RAG | No Disagreement | No Hallucination Check | No Retry")
    print("=" * 80)

    data = load_handoff_data()
    match_context = data['match_context']
    all_events = data['events']

    print(f"\nLoaded {len(all_events)} events for {match_context['home_team']} vs {match_context['away_team']}")

    # Select clips once — same for all preferences
    print("\nSelecting clips...")
    selected_events = select_clips(all_events)

    all_results = []

    for i, preference in enumerate(preferences, 1):
        print(f"\n[{i}/{len(preferences)}] Preference: {preference[:60]}...")
        print("-" * 80)

        start_time = time.time()

        try:
            # Build prompt
            prompt = build_prompt(match_context, selected_events, preference)

            # Single LLM call
            response = call_groq(prompt)
            time_taken = round(time.time() - start_time, 2)

            # Parse captions
            captions = parse_captions(response['text'], len(selected_events))

            # Compute alignment score
            alignment_score = compute_alignment_score(captions, preference)

            print(f"  [OK] {len(captions)} captions in {time_taken}s")
            print(f"  Alignment score: {alignment_score:.3f}")
            for j, caption in enumerate(captions, 1):
                print(f"  {j}. {caption}")

            all_results.append({
                "preference": preference,
                "captions": captions,
                "alignment_score": alignment_score,
                "time_taken": time_taken,
                "tokens_used": response['tokens_used'],
                "prompt_tokens": response['prompt_tokens'],
                "completion_tokens": response['completion_tokens'],
                "clip_count": len(captions),
                "status": "success",
            })

        except Exception as e:
            print(f"  ✗ Error: {e}")
            all_results.append({
                "preference": preference,
                "captions": [],
                "alignment_score": 0.0,
                "time_taken": 0.0,
                "tokens_used": None,
                "status": "error",
                "error": str(e),
            })

    # Summary statistics
    successful = [r for r in all_results if r['status'] == 'success']
    avg_alignment = round(sum(r['alignment_score'] for r in successful) / len(successful), 3) if successful else 0.0
    avg_time = round(sum(r['time_taken'] for r in successful) / len(successful), 2) if successful else 0.0

    print("\n" + "=" * 80)
    print("BASELINE 1 SUMMARY")
    print("=" * 80)
    print(f"Successful runs: {len(successful)}/{len(preferences)}")
    print(f"Average alignment score: {avg_alignment:.3f}")
    print(f"Average time per run: {avg_time:.2f}s")
    print(f"Hallucination rate: Not checked (no hallucination detection in baseline)")

    # Save results
    output = {
        "match_name": MATCH_NAME,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "baseline": "single_prompt",
        "description": "Single LLM call per preference. No RAG, no disagreement, no hallucination check, no retry.",
        "model": GROQ_MODEL,
        "clips_used": len(selected_events),
        "summary": {
            "total_runs": len(preferences),
            "successful_runs": len(successful),
            "avg_alignment_score": avg_alignment,
            "avg_time_seconds": avg_time,
            "hallucination_rate": "N/A — not checked",
        },
        "results": all_results,
    }

    output_path = Path(backend_dir) / "Outputs" / MATCH_NAME / "baseline_single_prompt_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Results saved to: {output_path}")
    print("=" * 80)


if __name__ == "__main__":
    run_baseline_single_prompt()
