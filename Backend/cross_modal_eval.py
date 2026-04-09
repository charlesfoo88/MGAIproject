"""
Cross-Modal Evaluation Script

Runs Gemini Vision blind (no API-Football hints) on the highlight video,
then compares detected events against API-Football ground truth.

Usage:
    python Backend/cross_modal_eval.py --match liverpool_2_0_man_city_2024_12_01 --video liverpool_2_0_man_city.mp4
"""

import json
import argparse
import time
from pathlib import Path
from datetime import datetime
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

BACKEND_DIR = Path(__file__).resolve().parent
SOURCE_VIDEOS_DIR = BACKEND_DIR / "Source_Videos"
MOCK_DATA_DIR = BACKEND_DIR / "Mock_Data"
OUTPUTS_DIR = BACKEND_DIR / "Outputs"

BLIND_PROMPT = """Watch this football highlights video carefully.

Without any prior knowledge of what happened in this match, identify every significant event you can see.

For each event return:
- event_type: one of [goal, penalty_goal, card, substitution, var_review]
- player: player name if visible on screen or in commentary
- team: team name if identifiable
- video_timestamp_seconds: seconds into this video where the event occurs
- confidence: high/medium/low

Return JSON only in this exact format:
{
  "detected_events": [
    {
      "event_type": "<type>",
      "player": "<name or null>",
      "team": "<team or null>",
      "video_timestamp_seconds": <seconds>,
      "confidence": "high/medium/low"
    }
  ]
}

Return JSON only, no other text."""


def run_blind_gemini_detection(video_path: Path) -> list:
    """Upload video and run blind event detection with Gemini Vision."""
    print(f"\n[Gemini Blind Detection] Uploading video: {video_path.name}...")
    
    video_file = gemini_client.files.upload(file=str(video_path))
    
    print("  → Processing", end="", flush=True)
    while video_file.state == "PROCESSING":
        print(".", end="", flush=True)
        time.sleep(2)
        video_file = gemini_client.files.get(name=video_file.name)
    print(" ✓")
    
    print("  → Running blind detection...")
    response = gemini_client.models.generate_content(
        model="gemini-2.5-pro",
        contents=[video_file, BLIND_PROMPT]
    )
    
    clean = response.text.replace("```json", "").replace("```", "").strip()
    result = json.loads(clean)
    detected = result.get("detected_events", [])
    
    print(f"  ✓ Gemini detected {len(detected)} events blind")
    return detected


def load_api_football_ground_truth(match_name: str) -> list:
    """Load API-Football events from approach_b_dl_handoff.json."""
    path = MOCK_DATA_DIR / match_name / "approach_b_dl_handoff.json"
    with open(path, 'r', encoding='utf-8') as f:
        handoff = json.load(f)
    
    events = [e for e in handoff.get("events", []) 
              if e.get("event_type") in ["goal", "penalty_goal", "card", "substitution", "var_review"]]
    
    print(f"  ✓ Loaded {len(events)} API-Football ground truth events")
    return events


def match_events(gemini_events: list, api_events: list, timestamp_tolerance_sec: int = 30) -> dict:
    """
    Compare Gemini blind detections against API-Football ground truth.
    
    Matching logic:
    - Same event_type AND
    - Gemini video_timestamp_seconds is within tolerance of clip_start_sec from API
    """
    matched = []
    unmatched_gemini = []
    unmatched_api = []
    
    api_matched = set()
    
    for g_event in gemini_events:
        g_type = g_event.get("event_type")
        g_ts = g_event.get("video_timestamp_seconds")
        
        if g_ts is None:
            unmatched_gemini.append(g_event)
            continue
        
        best_match = None
        best_deviation = float("inf")
        best_idx = None
        
        for idx, a_event in enumerate(api_events):
            if idx in api_matched:
                continue
            
            a_type = a_event.get("event_type")
            a_ts = a_event.get("clip_start_sec")
            
            if a_ts is None:
                continue
            
            if g_type == a_type:
                deviation = abs(g_ts - a_ts)
                if deviation < best_deviation:
                    best_deviation = deviation
                    best_match = a_event
                    best_idx = idx
        
        if best_match and best_deviation <= timestamp_tolerance_sec:
            api_matched.add(best_idx)
            matched.append({
                "event_type": g_type,
                "player_api": best_match.get("players", [None])[0],
                "player_gemini": g_event.get("player"),
                "api_clip_start_sec": best_match.get("clip_start_sec"),
                "gemini_timestamp_seconds": g_ts,
                "deviation_seconds": round(best_deviation, 1),
                "confidence": g_event.get("confidence"),
                "agreement": "high" if best_deviation <= 15 else "medium" if best_deviation <= 30 else "low"
            })
        else:
            unmatched_gemini.append(g_event)
    
    for idx, a_event in enumerate(api_events):
        if idx not in api_matched:
            unmatched_api.append(a_event)
    
    total_api = len(api_events)
    total_matched = len(matched)
    agreement_rate = round(total_matched / total_api, 3) if total_api > 0 else 0.0
    mean_deviation = round(sum(e["deviation_seconds"] for e in matched) / len(matched), 1) if matched else 0.0
    
    return {
        "total_api_events": total_api,
        "total_gemini_detections": len(gemini_events),
        "matched": total_matched,
        "unmatched_gemini": len(unmatched_gemini),
        "unmatched_api": len(unmatched_api),
        "agreement_rate": agreement_rate,
        "mean_deviation_seconds": mean_deviation,
        "matched_events": matched,
        "unmatched_api_events": unmatched_api,
        "unmatched_gemini_events": unmatched_gemini
    }


def main():
    parser = argparse.ArgumentParser(description="Cross-Modal Blind Evaluation")
    parser.add_argument("--match", required=True, help="Match folder name")
    parser.add_argument("--video", required=True, help="Video filename in Source_Videos/")
    parser.add_argument("--tolerance", type=int, default=30, help="Timestamp tolerance in seconds (default: 30)")
    args = parser.parse_args()
    
    video_path = SOURCE_VIDEOS_DIR / args.video
    
    print("=" * 60)
    print("CROSS-MODAL BLIND EVALUATION")
    print("=" * 60)
    print(f"Match: {args.match}")
    print(f"Video: {args.video}")
    print(f"Timestamp tolerance: ±{args.tolerance}s")
    
    # Step 1: Blind Gemini detection
    gemini_events = run_blind_gemini_detection(video_path)
    
    # Step 2: Load API-Football ground truth
    print(f"\n[Ground Truth] Loading API-Football events...")
    api_events = load_api_football_ground_truth(args.match)
    
    # Step 3: Compare
    print(f"\n[Matching] Comparing detections against ground truth...")
    results = match_events(gemini_events, api_events, args.tolerance)
    
    # Step 4: Save results
    output_path = OUTPUTS_DIR / args.match / "cross_modal_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    final_output = {
        "match": args.match,
        "timestamp": datetime.now().isoformat(),
        "timestamp_tolerance_seconds": args.tolerance,
        "gemini_blind_detections": gemini_events,
        "results": results
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)
    
    # Step 5: Print summary
    print("\n" + "=" * 60)
    print("CROSS-MODAL AGREEMENT SUMMARY")
    print("=" * 60)
    print(f"API-Football events:      {results['total_api_events']}")
    print(f"Gemini blind detections:  {results['total_gemini_detections']}")
    print(f"Matched:                  {results['matched']}")
    print(f"Agreement rate:           {results['agreement_rate']:.1%}")
    print(f"Mean deviation:           {results['mean_deviation_seconds']}s")
    print(f"\n✓ Results saved to: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
