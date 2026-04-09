"""
Approach A Ingestor — DL Highlight Video Extraction (Quick Test)

This script uses Gemini 2.5 Flash Vision to autonomously extract highlight events
from a preprocessed football highlight reel. No external API needed.

Usage:
    python Backend/Tools/approach_a_ingestor.py --match liverpool_2_0_man_city_2024_12_01 --video extended_highlights.mp4

This is a feasibility test — it only extracts and saves raw results for review.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

# API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    print("❌ Error: GEMINI_API_KEY not found in .env file")
    sys.exit(1)

# Initialize Gemini client
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# Paths
BACKEND_DIR = Path(__file__).parent.parent
SOURCE_VIDEOS_DIR = BACKEND_DIR / "Source_Videos"
OUTPUTS_DIR = BACKEND_DIR / "Outputs"


def extract_events_from_video(video_path: Path, model_name: str = "gemini-2.5-flash"):
    """
    Use Gemini Vision to extract highlight events from preprocessed video.
    
    Args:
        video_path: Path to the highlight video file
        model_name: Gemini model to use
        
    Returns:
        Dictionary with extracted events and match summary
    """
    print(f"\n[Gemini Vision] Analyzing video: {video_path.name}")
    print(f"  Model: {model_name}")
    
    # Upload video
    print("  Uploading video to Gemini...")
    video_file = gemini_client.files.upload(file=str(video_path))
    
    # Wait for processing
    print(f"  → Processing", end="", flush=True)
    while video_file.state == "PROCESSING":
        print(".", end="", flush=True)
        time.sleep(2)
        video_file = gemini_client.files.get(name=video_file.name)
    print(f" ✓")
    
    print(f"  ✓ Video uploaded: {video_file.name}")
    
    # Extraction prompt
    prompt = """Watch this football highlight reel carefully.

For each highlight event you can identify, extract:
- event_type (goal, penalty_goal, card, substitution, penalty_miss, var_review, disallowed_goal)
- team (which team was involved)
- players (player names if visible on screen or mentioned)
- video_timestamp_seconds (when in the video this happens)
- score_after_event (if scoreboard visible, format: "2-0")
- match_minute (if match clock visible, format: "45+2" or "67")
- narrative (one sentence describing what happened)

Return JSON only:
{
  "events": [
    {
      "event_type": "goal",
      "team": "Liverpool",
      "players": ["Mohamed Salah"],
      "video_timestamp_seconds": 15.5,
      "score_after_event": "1-0",
      "match_minute": "18",
      "narrative": "Mohamed Salah scores from inside the box after a through ball"
    }
  ],
  "match_summary": "one sentence summary of the match"
}

Return JSON only, no other text."""

    # Send request
    print("  Analyzing video content...")
    try:
        response = gemini_client.models.generate_content(
            model=model_name,
            contents=[video_file, prompt]
        )
        
        # Parse response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        result = json.loads(response_text)
        
        print(f"  ✓ Extraction complete: {len(result.get('events', []))} events found")
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"  ❌ Failed to parse Gemini response as JSON: {e}")
        print(f"  Raw response: {response.text[:500]}...")
        return None
    except Exception as e:
        print(f"  ❌ Error during extraction: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Approach A: Extract events from DL highlight video")
    parser.add_argument("--match", required=True, help="Match name (e.g., liverpool_2_0_man_city_2024_12_01)")
    parser.add_argument("--video", required=True, help="Video filename in Source_Videos/approach a/ folder")
    
    args = parser.parse_args()
    
    print("\n" + "=" * 80)
    print("APPROACH A INGESTOR — DL HIGHLIGHT VIDEO EXTRACTION (TEST)")
    print("=" * 80)
    print(f"Match: {args.match}")
    print(f"Video: {args.video}")
    
    # Locate video file
    video_path = SOURCE_VIDEOS_DIR / "approach a" / args.video
    
    if not video_path.exists():
        print(f"\n❌ Error: Video file not found at {video_path}")
        print(f"   Please place video in: {SOURCE_VIDEOS_DIR / 'approach a'}/")
        sys.exit(1)
    
    print(f"Video path: {video_path}")
    print(f"Video size: {video_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Create output directory
    output_dir = OUTPUTS_DIR / args.match
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract events
    result = extract_events_from_video(video_path)
    
    if result is None:
        print("\n❌ Extraction failed")
        sys.exit(1)
    
    # Save raw extraction results
    output_file = output_dir / "approach_a_extraction.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Raw extraction saved to: {output_file}")
    
    # Print results summary
    print("\n" + "=" * 80)
    print("EXTRACTION RESULTS")
    print("=" * 80)
    
    events = result.get('events', [])
    print(f"\nTotal events extracted: {len(events)}")
    
    if 'match_summary' in result:
        print(f"\nMatch summary: {result['match_summary']}")
    
    print("\nExtracted events:")
    for i, event in enumerate(events, 1):
        print(f"\n[{i}] {event.get('event_type', '?').upper()}")
        print(f"    Team: {event.get('team', '?')}")
        print(f"    Players: {', '.join(event.get('players', ['?']))}")
        print(f"    Match minute: {event.get('match_minute', '?')}")
        print(f"    Video timestamp: {event.get('video_timestamp_seconds', '?')}s")
        print(f"    Score after: {event.get('score_after_event', '?')}")
        print(f"    Narrative: {event.get('narrative', '?')}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE - Review results to assess feasibility")
    print("=" * 80)
    print(f"\n✓ If quality looks good, we can proceed with full Approach A implementation")
    print(f"✓ Results saved to: {output_file}")


if __name__ == "__main__":
    main()
