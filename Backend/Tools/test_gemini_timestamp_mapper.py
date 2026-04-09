"""
Test: Can Gemini Vision map match events to video timestamps?
Input: Arsenal 5-1 Man City highlights video + known goal scorers from API
Output: Each goal mapped to video timestamp in seconds
"""
import google.generativeai as genai
import os
import time
import json
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Known events from API-Football
known_events = [
    {"minute": "2", "event_type": "goal", "team": "Arsenal", "player": "M. Ødegaard"},
    {"minute": "25", "event_type": "card", "team": "Arsenal", "player": "Jurrien Timber"},
    {"minute": "55", "event_type": "goal", "team": "Manchester City", "player": "E. Haaland"},
    {"minute": "56", "event_type": "goal", "team": "Arsenal", "player": "T. Partey"},
    {"minute": "62", "event_type": "goal", "team": "Arsenal", "player": "M. Lewis-Skelly"},
    {"minute": "76", "event_type": "goal", "team": "Arsenal", "player": "K. Havertz"},
    {"minute": "90", "event_type": "goal", "team": "Arsenal", "player": "E. Nwaneri"},
]

video_path = Path(__file__).parent.parent / "Source_Videos" / "arsenal_5_1_man_city.mp4"

if not video_path.exists():
    print(f"❌ Video not found: {video_path}")
    exit(1)

print("Uploading video to Gemini...")
video_file = genai.upload_file(path=str(video_path), mime_type="video/mp4")
print(f"✓ Uploaded: {video_file.name}")

print("Waiting for processing...", end="", flush=True)
while video_file.state.name == "PROCESSING":
    print(".", end="", flush=True)
    time.sleep(2)
    video_file = genai.get_file(video_file.name)
print(f"\n✓ Ready: {video_file.state.name}")

model = genai.GenerativeModel("gemini-2.5-flash")

prompt = f"""Watch this football highlights video carefully.

I know these events happened in the match:
{json.dumps(known_events, indent=2)}

For each event, find exactly where it appears in this highlights video and return the video timestamp in seconds.

Return JSON only in this exact format:
{{
  "mapped_events": [
    {{
      "player": "<player name>",
      "event_type": "<goal/card>",
      "team": "<team>",
      "match_minute": "<minute from API>",
      "video_timestamp_seconds": <seconds into this video>,
      "clip_start_sec": <video_timestamp - 2>,
      "clip_end_sec": <video_timestamp + 8>,
      "found": true/false,
      "confidence": "high/medium/low"
    }}
  ]
}}

If you cannot find an event in the video set found=false.
Return JSON only, no other text."""

print("\nAsking Gemini to map events to video timestamps...")
response = model.generate_content([video_file, prompt])

print("\n=== Gemini Timestamp Mapping Result ===")
print(response.text)

# Save result
output_path = Path(__file__).parent.parent / "Outputs" / "arsenal_5_1_man_city_2025_02_02" / "gemini_timestamp_mapping.json"
output_path.parent.mkdir(parents=True, exist_ok=True)
try:
    clean = response.text.replace("```json", "").replace("```", "").strip()
    result = json.loads(clean)
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\n✓ Saved to: {output_path}")
except:
    print("\n⚠ Could not parse JSON — check raw output above")

print("\n=== Analysis Complete ===")
