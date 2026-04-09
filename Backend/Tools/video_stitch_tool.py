"""
Video Stitch Tool - Extract and concatenate video clips with subtitles

Uses ffmpeg-python to extract highlight clips from source video, stitch them together,
and attach generated WebVTT subtitles for the MGAI video highlight pipeline.
"""

import ffmpeg
import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict

# Configure FFmpeg path - use project-local ffmpeg
# FFmpeg binaries are located in Backend/Tools/ffmpeg/
FFMPEG_BIN_PATH = str(Path(__file__).parent / "ffmpeg")
if FFMPEG_BIN_PATH not in os.environ.get("PATH", ""):
    os.environ["PATH"] = FFMPEG_BIN_PATH + os.pathsep + os.environ.get("PATH", "")

# Handle both module import and direct execution
try:
    from ..config import OUTPUT_PATH
except ImportError:
    # Direct execution - add parent directory to path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from config import OUTPUT_PATH


def extract_and_stitch(
    source_mp4_path: str,
    events: List[Dict],
    captions: Dict[str, str],
    output_path: str
) -> str:
    """
    Extract clips from source video, stitch them together, and add subtitles.
    
    Args:
        source_mp4_path: Path to the source .mp4 video file
        events: List of event dictionaries, each containing:
            - clip_start_sec (float): Start time in seconds
            - clip_end_sec (float): End time in seconds
            - segment_id (str): Unique identifier for matching with captions
        captions: Dictionary mapping segment_id -> caption text string
        output_path: Path where the final stitched video should be saved
        
    Returns:
        str: The output_path of the generated video file
        
    Raises:
        FileNotFoundError: If source_mp4_path doesn't exist
        ValueError: If events list is empty
        RuntimeError: If ffmpeg operations fail
        
    Example:
        events = [
            {"segment_id": "seg_1", "clip_start_sec": 10.5, "clip_end_sec": 15.2},
            {"segment_id": "seg_2", "clip_start_sec": 45.0, "clip_end_sec": 52.3}
        ]
        captions = {
            "seg_1": "Saka's brilliant run down the wing",
            "seg_2": "Haaland scores with a powerful header"
        }
        output = extract_and_stitch("match.mp4", events, captions, "highlights.mp4")
    """
    # Validate inputs
    if not os.path.exists(source_mp4_path):
        raise FileNotFoundError(f"Source video not found: {source_mp4_path}")
    
    if not events:
        raise ValueError("Events list cannot be empty")
    
    print(f"Processing {len(events)} clips from {source_mp4_path}")
    
    # Create temp directory for intermediate files
    temp_dir = tempfile.mkdtemp(prefix="video_stitch_")
    print(f"Using temp directory: {temp_dir}")
    
    try:
        # Step 1: Extract individual clips
        clip_paths = []
        for idx, event in enumerate(events):
            clip_start = event.get("clip_start_sec", 0)
            clip_end = event.get("clip_end_sec", 0)
            segment_id = event.get("segment_id", f"seg_{idx}")
            
            clip_path = os.path.join(temp_dir, f"clip_{idx:03d}.mp4")
            duration = clip_end - clip_start
            
            print(f"  Extracting clip {idx + 1}/{len(events)}: {clip_start:.2f}s - {clip_end:.2f}s ({duration:.2f}s)")
            
            try:
                # Extract clip using ffmpeg-python with re-encoding to fix keyframe issues
                (
                    ffmpeg
                    .input(source_mp4_path, ss=clip_start, t=duration)
                    .output(
                        clip_path,
                        **{'c:v': 'libx264', 'c:a': 'aac', 'crf': '18', 'preset': 'fast'}
                    )
                    .overwrite_output()
                    .run(quiet=True, capture_stdout=True, capture_stderr=True)
                )
                clip_paths.append(clip_path)
                print(f"    ✓ Clip {idx + 1} extracted")
                
            except ffmpeg.Error as e:
                stderr = e.stderr.decode() if e.stderr else "Unknown error"
                print(f"    ✗ Failed to extract clip {idx + 1}: {stderr}")
                raise RuntimeError(f"Failed to extract clip {idx + 1}: {stderr}")
        
        # Step 2: Concatenate clips
        if len(clip_paths) == 1:
            # Single clip - just copy it
            print("Single clip - copying directly")
            temp_output = clip_paths[0]
        else:
            # Multiple clips - concatenate them
            print(f"Concatenating {len(clip_paths)} clips...")
            concat_file = os.path.join(temp_dir, "concat_list.txt")
            
            # Create concat file for ffmpeg
            with open(concat_file, 'w', encoding='utf-8') as f:
                for clip_path in clip_paths:
                    # Use absolute paths for concat
                    f.write(f"file '{clip_path}'\n")
            
            temp_output = os.path.join(temp_dir, "stitched_no_subs.mp4")
            
            try:
                # Concatenate using ffmpeg concat demuxer with re-encoding
                (
                    ffmpeg
                    .input(concat_file, format='concat', safe=0)
                    .output(
                        temp_output,
                        **{'c:v': 'libx264', 'c:a': 'aac', 'crf': '18', 'preset': 'fast'}
                    )
                    .overwrite_output()
                    .run(quiet=True, capture_stdout=True, capture_stderr=True)
                )
                print("  ✓ Clips concatenated successfully")
                
                # Step 2.5: Trim to exact duration to fix precision issues
                expected_duration = sum(event["clip_end_sec"] - event["clip_start_sec"] for event in events)
                print(f"  Trimming to exact duration: {expected_duration:.2f}s...")
                
                temp_trimmed = os.path.join(temp_dir, "stitched_trimmed.mp4")
                (
                    ffmpeg
                    .input(temp_output)
                    .output(temp_trimmed, t=expected_duration, c='copy')
                    .overwrite_output()
                    .run(quiet=True, capture_stdout=True, capture_stderr=True)
                )
                temp_output = temp_trimmed  # Use trimmed version
                print("  ✓ Video trimmed to exact duration")
                
            except ffmpeg.Error as e:
                stderr = e.stderr.decode() if e.stderr else "Unknown error"
                print(f"  ✗ Concatenation failed: {stderr}")
                raise RuntimeError(f"Concatenation failed: {stderr}")
        
        # Step 3: Generate WebVTT subtitle file
        vtt_path = os.path.join(temp_dir, "subtitles.vtt")
        print("Generating WebVTT subtitles...")
        
        # Import config for typing effect settings
        try:
            from ..config import ENABLE_TYPING_EFFECT, TYPING_SPEED_CPS
        except ImportError:
            from config import ENABLE_TYPING_EFFECT, TYPING_SPEED_CPS
        
        with open(vtt_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            
            cumulative_time = 0.0
            cue_counter = 1
            
            for idx, event in enumerate(events):
                segment_id = event.get("segment_id", f"seg_{idx}")
                caption_text = captions.get(segment_id, "")
                
                if not caption_text:
                    continue  # Skip if no caption for this segment
                
                # Calculate timing for this clip in the stitched video
                clip_duration = event["clip_end_sec"] - event["clip_start_sec"]
                clip_start = cumulative_time
                clip_end = cumulative_time + clip_duration
                cumulative_time = clip_end
                
                if ENABLE_TYPING_EFFECT and caption_text:
                    # Create progressive reveal effect (character-by-character)
                    char_duration = 1.0 / TYPING_SPEED_CPS  # seconds per character
                    
                    for char_idx in range(1, len(caption_text) + 1):
                        partial_text = caption_text[:char_idx]
                        
                        # Calculate timing for this character reveal
                        char_start = clip_start + (char_idx - 1) * char_duration
                        
                        # End time: either when next char appears, or end of clip
                        if char_idx < len(caption_text):
                            char_end = clip_start + char_idx * char_duration
                        else:
                            char_end = clip_end  # Last char stays until clip ends
                        
                        # Don't exceed clip duration
                        char_start = min(char_start, clip_end)
                        char_end = min(char_end, clip_end)
                        
                        if char_start >= clip_end:
                            break  # No more time for this character
                        
                        # Format time as HH:MM:SS.mmm
                        start_str = _format_vtt_time(char_start)
                        end_str = _format_vtt_time(char_end)
                        
                        # Write subtitle cue
                        f.write(f"{cue_counter}\n")
                        f.write(f"{start_str} --> {end_str}\n")
                        f.write(f"{partial_text}\n\n")
                        cue_counter += 1
                else:
                    # No typing effect - show full caption at once
                    start_str = _format_vtt_time(clip_start)
                    end_str = _format_vtt_time(clip_end)
                    
                    f.write(f"{cue_counter}\n")
                    f.write(f"{start_str} --> {end_str}\n")
                    f.write(f"{caption_text}\n\n")
                    cue_counter += 1
        
        print(f"  ✓ Generated {cue_counter - 1} subtitle cues")
        
        # Step 4: Attach subtitles to video
        print("Attaching subtitles to video...")
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        try:
            # Add subtitles using ffmpeg
            video = ffmpeg.input(temp_output)
            subtitles = ffmpeg.input(vtt_path)
            
            (
                ffmpeg
                .output(
                    video,
                    subtitles,
                    output_path,
                    **{'c:v': 'copy', 'c:a': 'copy', 'c:s': 'mov_text'}
                )
                .overwrite_output()
                .run(quiet=True, capture_stdout=True, capture_stderr=True)
            )
            print(f"  ✓ Subtitles attached successfully")
            
        except ffmpeg.Error as e:
            stderr = e.stderr.decode() if e.stderr else "Unknown error"
            print(f"  ✗ Failed to attach subtitles: {stderr}")
            raise RuntimeError(f"Failed to attach subtitles: {stderr}")
        
        # Step 5: Save standalone VTT file alongside MP4
        standalone_vtt_path = output_path.replace('.mp4', '.vtt')
        shutil.copy2(vtt_path, standalone_vtt_path)
        print(f"✓ Standalone subtitle file saved: {standalone_vtt_path}")
        
        print(f"✓ Final video saved to: {output_path}")
        return output_path
    
    finally:
        # Clean up temp directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"✓ Cleaned up temp directory")


def _format_vtt_time(seconds: float) -> str:
    """
    Format seconds as WebVTT time string (HH:MM:SS.mmm).
    
    Args:
        seconds: Time in seconds (can be float)
        
    Returns:
        str: Formatted time string like "00:01:23.456"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


# Test harness
if __name__ == "__main__":
    print("=" * 70)
    print("Video Stitch Tool - Test")
    print("=" * 70)
    print()
    
    # Note: This is a mock test since we don't have actual video files
    # In real usage, you would provide a real source video
    
    print("[Test 1] Testing VTT time formatting...")
    test_times = [0, 1.5, 65.123, 3661.789]
    for t in test_times:
        formatted = _format_vtt_time(t)
        print(f"  {t:10.3f}s -> {formatted}")
    print()
    
    print("[Test 2] Mock extract_and_stitch call (would fail without real video)...")
    print("  Example usage:")
    print()
    print("  events = [")
    print("      {'segment_id': 'seg_1', 'clip_start_sec': 10.5, 'clip_end_sec': 15.2},")
    print("      {'segment_id': 'seg_2', 'clip_start_sec': 45.0, 'clip_end_sec': 52.3}")
    print("  ]")
    print()
    print("  captions = {")
    print("      'seg_1': 'Saka\\'s brilliant run down the wing',")
    print("      'seg_2': 'Haaland scores with a powerful header'")
    print("  }")
    print()
    print("  output = extract_and_stitch(")
    print("      'source.mp4',")
    print("      events,")
    print("      captions,")
    print("      'highlights.mp4'")
    print("  )")
    print()
    
    print("[Test 3] Testing error handling...")
    
    # Test missing source file
    try:
        extract_and_stitch(
            "nonexistent.mp4",
            [{"segment_id": "seg_1", "clip_start_sec": 0, "clip_end_sec": 5}],
            {"seg_1": "Test"},
            "output.mp4"
        )
        print("  ✗ Should have raised FileNotFoundError")
    except FileNotFoundError as e:
        print(f"  ✓ Correctly raised FileNotFoundError: {e}")
    
    # Test empty events
    try:
        extract_and_stitch(
            "test.mp4",
            [],
            {},
            "output.mp4"
        )
        print("  ✗ Should have raised ValueError")
    except ValueError as e:
        print(f"  ✓ Correctly raised ValueError: {e}")
    except FileNotFoundError:
        print("  ✓ Correctly validated (file check happened first)")
    
    print()
    print("=" * 70)
    print("Tests completed!")
    print()
    print("Note: To test with real video, provide:")
    print("  - A source .mp4 file")
    print("  - Events with valid clip_start_sec and clip_end_sec")
    print("  - Captions dict with segment_id mappings")
    print("=" * 70)
