"""Quick test — can Gemini Vision extract soccer events from a video clip?"""
import google.generativeai as genai
import os
import time
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Option 1: Use local video file
# Download a short clip from https://www.youtube.com/watch?v=f3POqcfPJZ8
# and save to Backend/Source_Videos/test_clip.mp4

# Option 2: Use YouTube URL directly (if supported)
# video_url = "https://www.youtube.com/watch?v=f3POqcfPJZ8"

# For this test, we'll use a local file
video_path = Path(__file__).parent.parent / "Source_Videos" / "test_clip.mp4"

if not video_path.exists():
    print(f"❌ Video file not found: {video_path}")
    print("\nTo test this:")
    print("1. Download a short clip from: https://www.youtube.com/watch?v=f3POqcfPJZ8")
    print(f"2. Save it as: {video_path}")
    print("3. Run this script again")
    exit(1)

print(f"Uploading video to Gemini: {video_path.name}")
video_file = genai.upload_file(path=str(video_path), mime_type="video/mp4")
print(f"✓ Uploaded: {video_file.name}")

# Wait for file to be processed (required for video files)
print("Waiting for video to be processed...", end="", flush=True)
while video_file.state.name == "PROCESSING":
    print(".", end="", flush=True)
    time.sleep(2)
    video_file = genai.get_file(video_file.name)

if video_file.state.name == "FAILED":
    raise ValueError(f"Video processing failed: {video_file.state.name}")

print(f"\n✓ Video ready: {video_file.state.name}")

# Ask Gemini to extract soccer events
# Use gemini-2.5-flash for latest video support
model = genai.GenerativeModel("gemini-2.5-flash")
prompt = """Watch this football/soccer video clip carefully.
Extract the following information and respond in JSON only:
{
  "events": [
    {
      "timestamp_seconds": <when in video>,
      "event_type": "goal/foul/substitution/card/other",
      "team": "<team name or jersey colour>",
      "players": ["<player names visible>"],
      "score": "<score shown on screen>",
      "match_time": "<clock shown on screen>",
      "narrative": "<1 sentence what happened>",
      "emotion": "high/medium/low"
    }
  ]
}
Return JSON only, no other text."""

print("Asking Gemini to analyse video...")
response = model.generate_content([video_file, prompt])
print("\n=== Gemini Response ===")
print(response.text)

print("\n=== Analysis Complete ===")
