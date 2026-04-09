"""
Quick script to manually update Liverpool match timestamps based on user-provided video review.

BACKGROUND:
Gemini Vision (all models: 2.5-flash, 1.5-flash, 2.5-pro) failed to automatically detect
the 2 goals in liverpool_2_0_man_city.mp4 after 5 attempts. All returned found=false.

SOLUTION:
Human manual review of the video (2026-04-05) to identify exact timestamps.
These timestamps were verified by watching the video and noting when the ball crosses
the goal line for each of the 2 Liverpool goals.

MANUAL TIMESTAMPS (provided by human review):
- Salah goal:       4:24 - 4:35 (264-275 seconds)  
- Szoboszlai goal: 11:52 - 12:02 (712-722 seconds)

This script updates both D15 (approach_b_highlight_candidates.json)
and D17 (approach_b_dl_handoff.json)
with these manually-verified timestamps to enable the MGAI pipeline to proceed.
"""
import json
from pathlib import Path

# User-provided timestamps (MM:SS format converted to seconds)
# NOTE: These are MANUALLY DETERMINED via human video review (2026-04-05)
# because Gemini Vision could not detect the goals automatically
SALAH_CLIP = (264, 275)      # 4:24 - 4:35 (11 seconds) - HUMAN VERIFIED
SZOBOSZLAI_CLIP = (712, 722) # 11:52 - 12:02 (10 seconds) - HUMAN VERIFIED

# Match name
MATCH_NAME = "liverpool_2_0_man_city_2025_02_23"

# Paths
BASE_DIR = Path(__file__).parent.parent
D15_PATH = BASE_DIR / "Mock_Data" / MATCH_NAME / "approach_b_highlight_candidates.json"
D17_PATH = BASE_DIR / "Mock_Data" / MATCH_NAME / "approach_b_dl_handoff.json"

print("="*70)
print("LIVERPOOL TIMESTAMP FIX")
print("="*70)
print(f"Salah goal: {SALAH_CLIP[0]}s - {SALAH_CLIP[1]}s")
print(f"Szoboszlai goal: {SZOBOSZLAI_CLIP[0]}s - {SZOBOSZLAI_CLIP[1]}s")

# Update D17 (approach_b_dl_handoff.json)
print(f"\n[1] Updating D17: {D17_PATH.name}")
with open(D17_PATH, 'r') as f:
    d17 = json.load(f)

updated_count = 0
for event in d17['events']:
    # Find Salah goal (segment_001, minute 14) - match by time
    if event.get('time') == '14:00' and event.get('event_type') == 'goal':
        event['clip_start_sec'] = SALAH_CLIP[0]
        event['clip_end_sec'] = SALAH_CLIP[1]
        print(f"  ✓ Updated {event['clip_id']}: Mohamed Salah goal (14') → {SALAH_CLIP[0]}-{SALAH_CLIP[1]}s")
        updated_count += 1
    
    # Find Szoboszlai goal (segment_002, minute 37) - match by time
    elif event.get('time') == '37:00' and event.get('event_type') == 'goal':
        event['clip_start_sec'] = SZOBOSZLAI_CLIP[0]
        event['clip_end_sec'] = SZOBOSZLAI_CLIP[1]
        print(f"  ✓ Updated {event['clip_id']}: Szoboszlai goal (37') → {SZOBOSZLAI_CLIP[0]}-{SZOBOSZLAI_CLIP[1]}s")
        updated_count += 1

with open(D17_PATH, 'w') as f:
    json.dump(d17, f, indent=2)
print(f"  → Saved {D17_PATH}")

# Update D15 (approach_b_highlight_candidates.json)
print(f"\n[2] Updating D15: {D15_PATH.name}")
with open(D15_PATH, 'r') as f:
    d15 = json.load(f)

updated_d15 = 0
for candidate in d15:
    # Find Salah goal (match minute 14)
    if candidate.get('match_time_display') == '14:00' and candidate.get('predicted_event_type') == 'goal':
        candidate['time_range']['start'] = SALAH_CLIP[0]
        candidate['time_range']['end'] = SALAH_CLIP[1]
        print(f"  ✓ Updated {candidate['segment_id']}: Mohamed Salah (14') → {SALAH_CLIP[0]}-{SALAH_CLIP[1]}s")
        updated_d15 += 1
    
    # Find Szoboszlai goal (match minute 37)
    elif candidate.get('match_time_display') == '37:00' and candidate.get('predicted_event_type') == 'goal':
        candidate['time_range']['start'] = SZOBOSZLAI_CLIP[0]
        candidate['time_range']['end'] = SZOBOSZLAI_CLIP[1]
        print(f"  ✓ Updated {candidate['segment_id']}: Szoboszlai (37') → {SZOBOSZLAI_CLIP[0]}-{SZOBOSZLAI_CLIP[1]}s")
        updated_d15 += 1

with open(D15_PATH, 'w') as f:
    json.dump(d15, f, indent=2)
print(f"  → Saved {D15_PATH}")

print("\n" + "="*70)
print(f"✅ COMPLETE: Updated {updated_count} events in D17, {updated_d15} in D15")
print("="*70)
print("\nNext step: Update config.py ACTIVE_MATCH = 'liverpool_2_0_man_city_2025_02_23'")
print("Then run: python Backend/pipeline.py")
