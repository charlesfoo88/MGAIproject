"""
Export embedded subtitles from MP4 files to standalone VTT files
"""
import ffmpeg
import sys
from pathlib import Path

def export_subtitles(video_path: str, output_vtt_path: str):
    """
    Extract embedded subtitles from MP4 to VTT file
    
    Args:
        video_path: Path to MP4 file with embedded subtitles
        output_vtt_path: Path where VTT file should be saved
    """
    try:
        # Extract subtitle stream and convert to WebVTT
        (
            ffmpeg
            .input(video_path)
            .output(output_vtt_path, map='0:s:0')  # Convert to webvtt automatically
            .overwrite_output()
            .run(quiet=True, capture_stdout=True, capture_stderr=True)
        )
        print(f"✓ Exported subtitles to: {output_vtt_path}")
        return True
    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "Unknown error"
        print(f"✗ Failed to export subtitles: {stderr}")
        return False

if __name__ == "__main__":
    # Export subtitles for all reel videos
    output_dir = Path(__file__).parent.parent / "Outputs" / "arsenal_5_1_man_city_2025_02_02"
    
    # Auto-discover all reel MP4 files (excluding test files)
    video_files = sorted([
        f.name for f in output_dir.glob("reel_*.mp4")
        if not f.name.startswith("reel_test")
    ])
    
    print("=" * 70)
    print("SUBTITLE EXPORT TOOL")
    print("=" * 70)
    print()
    
    for video_name in video_files:
        video_path = output_dir / video_name
        vtt_path = output_dir / video_name.replace(".mp4", ".vtt")
        print(f"Exporting subtitles from {video_name}...")
        export_subtitles(str(video_path), str(vtt_path))
    
    print()
    print("=" * 70)
    print("✅ EXPORT COMPLETE")
    print("=" * 70)
    print()
    print("To use subtitles:")
    print("1. Open the video in your player")
    print("2. When asked for subtitle file, browse to:")
    print(f"   {output_dir}")
    print("3. Select the matching .vtt file (e.g., reel_a.vtt)")
