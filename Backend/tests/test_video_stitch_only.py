"""Test video stitching only - no LLM calls"""
import sys
from pathlib import Path

# Setup paths
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from Tools import video_stitch_tool

# Test data - 5 goal highlights from Arsenal 5-1 Man City
test_events = [
    {"segment_id": "segment_001", "clip_start_sec": 87.0, "clip_end_sec": 97.0},
    {"segment_id": "segment_004", "clip_start_sec": 437.0, "clip_end_sec": 447.0},
    {"segment_id": "segment_005", "clip_start_sec": 484.0, "clip_end_sec": 494.0},
    {"segment_id": "segment_009", "clip_start_sec": 541.0, "clip_end_sec": 551.0},
    {"segment_id": "segment_014", "clip_start_sec": 589.0, "clip_end_sec": 599.0},
]

test_captions = {
    "segment_001": "What a start! M. Ødegaard scores for Arsenal at 2 minutes.",
    "segment_004": "T. Partey strikes! Arsenal go 2-1 up at 56 minutes.",
    "segment_005": "M. Lewis-Skelly scores! Arsenal extend their lead at 62 minutes.",
    "segment_009": "K. Havertz scores! Arsenal now lead 4-1 at 76 minutes.",
    "segment_014": "E. Nwaneri seals it! Arsenal win 5-1 at 90 minutes.",
}

# Paths
source_video = backend_dir / "Source_Videos" / "test_clip.mp4"
output_dir = backend_dir / "Outputs" / "arsenal_5_1_man_city_2025_02_02"
output_dir.mkdir(parents=True, exist_ok=True)
output_path = str(output_dir / "reel_test.mp4")

print("="*70)
print("VIDEO STITCHING TEST")
print("="*70)
print(f"Source video: {source_video}")
print(f"Output path: {output_path}")
print(f"Events to stitch: {len(test_events)}")
print("="*70)

try:
    result = video_stitch_tool.extract_and_stitch(
        source_mp4_path=str(source_video),
        events=test_events,
        captions=test_captions,
        output_path=output_path
    )
    print("\n" + "="*70)
    print("✅ VIDEO STITCHING SUCCESSFUL!")
    print("="*70)
    print(f"Output file: {result}")
    print(f"File size: {Path(result).stat().st_size / 1024 / 1024:.2f} MB")
    print("="*70)
except Exception as e:
    print("\n" + "="*70)
    print("❌ VIDEO STITCHING FAILED")
    print("="*70)
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
