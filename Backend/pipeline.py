"""
MGAI Pipeline Orchestrator

Main pipeline that runs all three agents (sports_analyst, fan, critic) in sequence
and stitches the final video reels.

Usage:
    from pipeline import run_pipeline
    result = run_pipeline(match_name="arsenal_vs_city_efl_2026", user_preference="I love Arsenal and Saka!")
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional

# Relative imports
try:
    from .State.shared_state import SharedState
    from .Agents import sports_analyst_agent, fan_agent, critic_agent
    from .Tools import video_stitch_tool
    from .config import (
        DEMO_MODE,
        OUTPUT_PATH,
        SOURCE_VIDEOS_PATH,
        SOURCE_VIDEO_PATH,
        ACTIVE_MATCH,
        MOCK_DATA_PATH,
    )
except ImportError:
    # Direct execution fallback
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from State.shared_state import SharedState
    from Agents import sports_analyst_agent, fan_agent, critic_agent
    from Tools import video_stitch_tool
    from config import (
        DEMO_MODE,
        OUTPUT_PATH,
        SOURCE_VIDEOS_PATH,
        SOURCE_VIDEO_PATH,
        ACTIVE_MATCH,
        MOCK_DATA_PATH,
    )


def run_pipeline(match_name: str, user_preference: str) -> dict:
    """
    Run the complete MGAI pipeline: analyze → caption → verify → stitch.
    
    Args:
        match_name: Unique identifier for the match (used in output filenames)
                   Example: "arsenal_vs_city_efl_2026"
        user_preference: User's preference string for personalization
                        Example: "I am an Arsenal fan and I love watching Saka play!"
    
    Returns:
        dict: Result dictionary containing:
            - reel_a_path (str): Path to personalized reel MP4
            - reel_b_path (str): Path to neutral reel MP4
            - reel_a_captions (list): List of caption strings for Reel A
            - reel_b_captions (list): List of caption strings for Reel B
            - hallucination_flagged (bool): Whether hallucinations were detected
            - retry_count (int): Number of retries used by critic agent
            - status (str): "success" or "error"
            - error_message (str, optional): Error details if status is "error"
    
    Example:
        >>> result = run_pipeline(
        ...     match_name="arsenal_vs_city_2026",
        ...     user_preference="I am an Arsenal fan and I love watching Saka play!"
        ... )
        >>> print(f"Personalized reel: {result['reel_a_path']}")
        >>> print(f"Captions: {result['reel_a_captions']}")
    """
    print("=" * 70)
    print("MGAI PIPELINE - Video Highlight Generation")
    print("=" * 70)
    print(f"Match: {match_name}")
    print(f"User preference: {user_preference}")
    print(f"Demo mode: {DEMO_MODE}")
    print("=" * 70)
    
    try:
        # ====================================================================
        # DEMO MODE: Return pre-generated outputs
        # ====================================================================
        if DEMO_MODE:
            print("\n[DEMO MODE] Loading pre-generated outputs...")
            print("⚠ Video stitching skipped in demo mode")
            print("⚠ Returning mock file paths")
            
            # In demo mode, we skip video processing and return mock paths
            # Actual demo output files would be in Backend/Outputs/ if they existed
            reel_a_path = str(OUTPUT_PATH / f"reel_a_{match_name}_demo.mp4")
            reel_b_path = str(OUTPUT_PATH / f"reel_b_{match_name}_demo.mp4")
            
            # Still run agents to get captions for demo
            shared_state = SharedState()
            shared_state.user_preference = user_preference
            
            print("\n[Stage 1] Running sports_analyst_agent...")
            print("-" * 70)
            shared_state = sports_analyst_agent.run(shared_state)
            print(f"✓ Filtered {len(shared_state.events)} events")
            print(f"✓ Preferred entity: {shared_state.preferred_entity}")
            
            print("\n[Stage 2] Running fan_agent...")
            print("-" * 70)
            shared_state = fan_agent.run(shared_state)
            print(f"✓ Reel A (Personalized): {len(shared_state.reel_a_events)} clips")
            print(f"✓ Reel B (Neutral): {len(shared_state.reel_b_events)} clips")
            
            print("\n[Stage 3] Running critic_agent...")
            print("-" * 70)
            verified_output = critic_agent.run(shared_state)
            print(f"✓ Verification complete")
            print(f"✓ Hallucinations flagged: {verified_output.hallucination_flagged}")
            print(f"✓ Retry count: {verified_output.retry_count}")
            
            # Extract captions
            reel_a_captions = [event.caption for event in verified_output.verified_reel_a]
            reel_b_captions = [event.caption for event in verified_output.verified_reel_b]
            
            # Extract event metadata
            reel_a_events = [
                {
                    "segment_id": event.segment_id,
                    "event_type": event.event_type,
                    "team": event.team,
                    "clip_start_sec": event.clip_start_sec,
                    "clip_end_sec": event.clip_end_sec,
                }
                for event in verified_output.verified_reel_a
            ]
            reel_b_events = [
                {
                    "segment_id": event.segment_id,
                    "event_type": event.event_type,
                    "team": event.team,
                    "clip_start_sec": event.clip_start_sec,
                    "clip_end_sec": event.clip_end_sec,
                }
                for event in verified_output.verified_reel_b
            ]
            
            print("\n" + "=" * 70)
            print("✅ DEMO PIPELINE COMPLETE")
            print("=" * 70)
            print(f"⚠ Note: Video files not created in demo mode")
            print(f"Reel A: {len(reel_a_captions)} captions")
            print(f"Reel B: {len(reel_b_captions)} captions")
            
            return {
                "reel_a_path": reel_a_path,
                "reel_b_path": reel_b_path,
                "reel_a_captions": reel_a_captions,
                "reel_b_captions": reel_b_captions,
                "reel_a_events": reel_a_events,
                "reel_b_events": reel_b_events,
                "hallucination_flagged": verified_output.hallucination_flagged,
                "retry_count": verified_output.retry_count,
                "reel_a_alignment_score": verified_output.reel_a_alignment_score,
                "reel_b_alignment_score": verified_output.reel_b_alignment_score,
                "preference_alignment_scores": verified_output.preference_alignment_scores,
                "match_recap": shared_state.match_recap,
                "status": "success",
            }
        
        # ====================================================================
        # PRODUCTION MODE: Run full pipeline with video stitching
        # ====================================================================
        
        # Initialize shared state
        print("\n[Initialization] Creating shared state...")
        shared_state = SharedState()
        shared_state.user_preference = user_preference
        print("✓ Shared state created")
        
        # ====================================================================
        # Stage 1: Sports Analyst Agent (Planner)
        # ====================================================================
        print("\n[Stage 1] Running sports_analyst_agent...")
        print("-" * 70)
        shared_state = sports_analyst_agent.run(shared_state)
        print(f"✓ Stage 1 complete")
        print(f"  - Filtered events: {len(shared_state.events)}")
        print(f"  - Preferred entity: {shared_state.preferred_entity}")
        
        # ====================================================================
        # Stage 2: Fan Agent (Executor)
        # ====================================================================
        print("\n[Stage 2] Running fan_agent...")
        print("-" * 70)
        shared_state = fan_agent.run(shared_state)
        print(f"✓ Stage 2 complete")
        print(f"  - Reel A (Personalized): {len(shared_state.reel_a_events)} clips")
        print(f"  - Reel B (Neutral): {len(shared_state.reel_b_events)} clips")
        print(f"  - Total captions generated: {len(shared_state.captions)}")
        
        # ====================================================================
        # Stage 3: Critic Agent (Evaluator)
        # ====================================================================
        print("\n[Stage 3] Running critic_agent...")
        print("-" * 70)
        verified_output = critic_agent.run(shared_state)
        print(f"✓ Stage 3 complete")
        print(f"  - Hallucinations detected: {verified_output.hallucination_flagged}")
        print(f"  - Retries used: {verified_output.retry_count}")
        print(f"  - Verified Reel A clips: {len(verified_output.verified_reel_a)}")
        print(f"  - Verified Reel B clips: {len(verified_output.verified_reel_b)}")
        
        # ====================================================================
        # Stage 4: Video Stitching
        # ====================================================================
        # Data sources for video stitching:
        # - Captions: From agent pipeline (verified_output.verified_reel_a/b)
        # - Timestamps: From fusion_summary.json (real ML detected time ranges)
        # This combines AI-generated captions with ML-detected video segments
        print("\n[Stage 4] Video stitching...")
        print("-" * 70)
        
        # Ensure output directory exists
        OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
        
        # Find source video file
        # Priority:
        # 1. Check SOURCE_VIDEO_PATH from config if it exists
        # 2. Fall back to D5 video_analysis_manifest.json
        # 3. Search for {match_name}.mp4 in SOURCE_VIDEOS_PATH
        # 4. Use any .mp4 in SOURCE_VIDEOS_PATH
        
        source_video = None
        
        # Option 1: Check SOURCE_VIDEO_PATH from config
        if SOURCE_VIDEO_PATH and SOURCE_VIDEO_PATH.exists():
            source_video = SOURCE_VIDEO_PATH
            print(f"✓ Using SOURCE_VIDEO_PATH from config: {source_video}")
        
        # Option 2: Try D5 video_analysis_manifest.json
        if not source_video:
            d5_path = MOCK_DATA_PATH / match_name / "video_analysis_manifest.json"
            if d5_path.exists():
                try:
                    with open(d5_path, 'r', encoding='utf-8') as f:
                        d5_data = json.load(f)
                    source_path_str = d5_data.get("source_path")
                    if source_path_str:
                        # Handle relative paths from Mock_Data folder
                        if not Path(source_path_str).is_absolute():
                            source_video = Path(__file__).parent / source_path_str
                        else:
                            source_video = Path(source_path_str)
                        
                        if source_video.exists():
                            print(f"✓ Using source from D5 manifest: {source_video}")
                        else:
                            print(f"⚠ D5 manifest source path doesn't exist: {source_video}")
                            source_video = None
                except Exception as e:
                    print(f"⚠ Could not read D5 manifest: {e}")
        
        # Option 3: Search for {match_name}.mp4
        if not source_video:
            candidate = SOURCE_VIDEOS_PATH / f"{match_name}.mp4"
            if candidate.exists():
                source_video = candidate
                print(f"✓ Using match-named video: {source_video}")
        
        # Option 4: Use any .mp4 in SOURCE_VIDEOS_PATH
        if not source_video:
            print(f"⚠ Source video not found with match name: {match_name}.mp4")
            print("⚠ Searching for any MP4 in Source_Videos/...")
            mp4_files = list(SOURCE_VIDEOS_PATH.glob("*.mp4"))
            if mp4_files:
                source_video = mp4_files[0]
                print(f"✓ Using: {source_video.name}")
        
        # Final check
        if not source_video or not source_video.exists():
            raise FileNotFoundError(
                f"No source video found. Tried:\n"
                f"  1. SOURCE_VIDEO_PATH: {SOURCE_VIDEO_PATH}\n"
                f"  2. D5 manifest: {MOCK_DATA_PATH / match_name / 'video_analysis_manifest.json'}\n"
                f"  3. Match-named: {SOURCE_VIDEOS_PATH / match_name}.mp4\n"
                f"  4. Any .mp4 in {SOURCE_VIDEOS_PATH}"
            )
        
        print(f"Source video: {source_video}")
        
        # Load fusion_summary.json for real ML timestamps
        fusion_path = Path(__file__).parent / "Mock_Data" / "fusion_summary.json"
        print(f"Loading fusion timestamps from: {fusion_path}")
        
        try:
            with open(fusion_path, 'r', encoding='utf-8') as f:
                fusion_data = json.load(f)
            fusion_highlights = fusion_data.get("highlights", [])
            
            # Create lookup dict: segment_id -> time_range
            fusion_lookup = {
                h["segment_id"]: h["time_range"]
                for h in fusion_highlights
            }
            print(f"  Loaded {len(fusion_lookup)} fusion timestamps")
        except FileNotFoundError:
            print(f"⚠ Warning: fusion_summary.json not found, using agent timestamps")
            fusion_lookup = {}
        except Exception as e:
            print(f"⚠ Warning: Could not parse fusion_summary.json: {e}")
            fusion_lookup = {}
        
        # Prepare Reel A events and captions
        # Use fusion timestamps if available, otherwise fall back to agent timestamps
        reel_a_events_dict = []
        reel_a_events = []
        for event in verified_output.verified_reel_a:
            segment_id = event.segment_id
            
            # Try to get fusion timestamps first
            if segment_id in fusion_lookup:
                time_range = fusion_lookup[segment_id]
                clip_start = time_range["start"]
                clip_end = time_range["end"]
                print(f"  Using fusion timestamp for {segment_id}: {clip_start:.1f}s - {clip_end:.1f}s")
            else:
                # Fallback to agent timestamps
                clip_start = event.clip_start_sec
                clip_end = event.clip_end_sec
                print(f"  Using agent timestamp for {segment_id}: {clip_start:.1f}s - {clip_end:.1f}s")
            
            reel_a_events_dict.append({
                "segment_id": segment_id,
                "clip_start_sec": clip_start,
                "clip_end_sec": clip_end,
            })
            
            # Store full event metadata for API response
            reel_a_events.append({
                "segment_id": segment_id,
                "event_type": event.event_type,
                "team": event.team,
                "clip_start_sec": clip_start,
                "clip_end_sec": clip_end,
            })
        
        reel_a_captions_dict = {
            event.segment_id: event.caption
            for event in verified_output.verified_reel_a
        }
        
        # Prepare Reel B events and captions
        reel_b_events_dict = []
        reel_b_events = []
        for event in verified_output.verified_reel_b:
            segment_id = event.segment_id
            
            # Try to get fusion timestamps first
            if segment_id in fusion_lookup:
                time_range = fusion_lookup[segment_id]
                clip_start = time_range["start"]
                clip_end = time_range["end"]
                print(f"  Using fusion timestamp for {segment_id}: {clip_start:.1f}s - {clip_end:.1f}s")
            else:
                # Fallback to agent timestamps
                clip_start = event.clip_start_sec
                clip_end = event.clip_end_sec
                print(f"  Using agent timestamp for {segment_id}: {clip_start:.1f}s - {clip_end:.1f}s")
            
            reel_b_events_dict.append({
                "segment_id": segment_id,
                "clip_start_sec": clip_start,
                "clip_end_sec": clip_end,
            })
            
            # Store full event metadata for API response
            reel_b_events.append({
                "segment_id": segment_id,
                "event_type": event.event_type,
                "team": event.team,
                "clip_start_sec": clip_start,
                "clip_end_sec": clip_end,
            })
        
        reel_b_captions_dict = {
            event.segment_id: event.caption
            for event in verified_output.verified_reel_b
        }
        
        # Stitch Reel A (Personalized)
        print("\n[4.1] Stitching Reel A (Personalized)...")
        
        # Create match-specific output directory
        match_output_dir = OUTPUT_PATH / match_name
        match_output_dir.mkdir(parents=True, exist_ok=True)
        
        reel_a_path = str(match_output_dir / "reel_a.mp4")
        try:
            video_stitch_tool.extract_and_stitch(
                source_mp4_path=str(source_video),
                events=reel_a_events_dict,
                captions=reel_a_captions_dict,
                output_path=reel_a_path
            )
            print(f"✓ Reel A saved: {reel_a_path}")
        except Exception as e:
            print(f"✗ Reel A stitching failed: {e}")
            raise
        
        # Stitch Reel B (Neutral)
        print("\n[4.2] Stitching Reel B (Neutral)...")
        reel_b_path = str(match_output_dir / "reel_b.mp4")
        try:
            video_stitch_tool.extract_and_stitch(
                source_mp4_path=str(source_video),
                events=reel_b_events_dict,
                captions=reel_b_captions_dict,
                output_path=reel_b_path
            )
            print(f"✓ Reel B saved: {reel_b_path}")
        except Exception as e:
            print(f"✗ Reel B stitching failed: {e}")
            raise
        
        # ====================================================================
        # Pipeline Complete
        # ====================================================================
        print("\n" + "=" * 70)
        print("✅ PIPELINE COMPLETE")
        print("=" * 70)
        print(f"Personalized Reel (A): {reel_a_path}")
        print(f"  - {len(verified_output.verified_reel_a)} clips")
        print(f"Neutral Reel (B): {reel_b_path}")
        print(f"  - {len(verified_output.verified_reel_b)} clips")
        print(f"Hallucinations detected: {verified_output.hallucination_flagged}")
        print(f"Retries used: {verified_output.retry_count}/{shared_state.retry_count}")
        print("=" * 70)
        
        # Extract caption lists
        reel_a_captions = [event.caption for event in verified_output.verified_reel_a]
        reel_b_captions = [event.caption for event in verified_output.verified_reel_b]
        
        return {
            "reel_a_path": reel_a_path,
            "reel_b_path": reel_b_path,
            "reel_a_captions": reel_a_captions,
            "reel_b_captions": reel_b_captions,
            "reel_a_events": reel_a_events,
            "reel_b_events": reel_b_events,
            "hallucination_flagged": verified_output.hallucination_flagged,
            "retry_count": verified_output.retry_count,
            "reel_a_alignment_score": verified_output.reel_a_alignment_score,
            "reel_b_alignment_score": verified_output.reel_b_alignment_score,
            "preference_alignment_scores": verified_output.preference_alignment_scores,
            "match_recap": shared_state.match_recap,
            "evidence_summary": verified_output.evidence_summary,
            "reel_a_evidence": [
                {
                    "segment_id": event.segment_id,
                    "rag_facts_used": event.evidence.rag_facts if event.evidence else [],
                    "d17_narrative": event.evidence.d17_fields.get("narrative") if event.evidence else None,
                    "importance_score": event.evidence.d15_fields.get("importance_score") if event.evidence else None,
                }
                for event in verified_output.verified_reel_a
            ],
            "reel_b_evidence": [
                {
                    "segment_id": event.segment_id,
                    "rag_facts_used": event.evidence.rag_facts if event.evidence else [],
                    "d17_narrative": event.evidence.d17_fields.get("narrative") if event.evidence else None,
                    "importance_score": event.evidence.d15_fields.get("importance_score") if event.evidence else None,
                }
                for event in verified_output.verified_reel_b
            ],
            "status": "success",
        }
    
    except FileNotFoundError as e:
        error_msg = f"File not found: {e}"
        print(f"\n✗ ERROR: {error_msg}")
        return {
            "reel_a_path": None,
            "reel_b_path": None,
            "reel_a_captions": [],
            "reel_b_captions": [],
            "hallucination_flagged": False,
            "retry_count": 0,
            "status": "error",
            "error_message": error_msg,
        }
    
    except Exception as e:
        error_msg = f"Pipeline error: {type(e).__name__}: {e}"
        print(f"\n✗ ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            "reel_a_path": None,
            "reel_b_path": None,
            "reel_a_captions": [],
            "reel_b_captions": [],
            "hallucination_flagged": False,
            "retry_count": 0,
            "status": "error",
            "error_message": error_msg,
        }


# ============================================================================
# CLI Entry Point (for direct execution)
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run MGAI video highlight pipeline")
    parser.add_argument(
        "--match-name",
        type=str,
        required=True,
        help="Match identifier (e.g., arsenal_vs_city_efl_2026)"
    )
    parser.add_argument(
        "--user-preference",
        type=str,
        default="I am an Arsenal fan and I love watching Saka play!",
        help="User preference string for personalization"
    )
    
    args = parser.parse_args()
    
    # Run pipeline
    result = run_pipeline(
        match_name=args.match_name,
        user_preference=args.user_preference
    )
    
    # Print result summary
    print("\n" + "=" * 70)
    print("PIPELINE RESULT")
    print("=" * 70)
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Reel A: {result['reel_a_path']} ({len(result['reel_a_captions'])} clips)")
        print(f"Reel B: {result['reel_b_path']} ({len(result['reel_b_captions'])} clips)")
        print(f"Hallucinations: {result['hallucination_flagged']}")
        print(f"Retries: {result['retry_count']}")
    else:
        print(f"Error: {result.get('error_message', 'Unknown error')}")
    print("=" * 70)
    
    # Exit with appropriate code
    sys.exit(0 if result['status'] == 'success' else 1)
