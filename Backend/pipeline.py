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
import os
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Fix Windows terminal encoding for Unicode characters (✓, ✗, etc.)
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Relative imports
try:
    from .State.shared_state import SharedState
    from .Schemas.verified_output_schema import VerifiedOutput
    from .Agents import sports_analyst_agent, fan_agent, critic_agent
    from .Agents.critic_agent import run_disagreement
    from .Tools import video_stitch_tool
    from .config import (
        DEMO_MODE,
        OUTPUT_PATH,
        SOURCE_VIDEOS_PATH,
        SOURCE_VIDEO_PATH,
        ACTIVE_MATCH,
        MOCK_DATA_PATH,
        LLM_PROVIDER,
    )
except ImportError:
    # Direct execution fallback
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from State.shared_state import SharedState
    from Schemas.verified_output_schema import VerifiedOutput
    from Agents import sports_analyst_agent, fan_agent, critic_agent
    from Agents.critic_agent import run_disagreement
    from Tools import video_stitch_tool
    from config import (
        DEMO_MODE,
        OUTPUT_PATH,
        SOURCE_VIDEOS_PATH,
        SOURCE_VIDEO_PATH,
        ACTIVE_MATCH,
        MOCK_DATA_PATH,
        LLM_PROVIDER,
    )


def write_evidence_log(
    match_name: str,
    user_preference: str,
    shared_state: SharedState,
    verified_output: VerifiedOutput,
    output_path: Path,
    perspective_name: str = None
) -> Path:
    """
    Write evidence log to track what went into each caption and how it was validated.
    
    Args:
        match_name: Match identifier
        user_preference: User preference string
        shared_state: SharedState with match context
        verified_output: VerifiedOutput from critic agent
        output_path: Directory to write evidence_log.json
        
    Returns:
        Path to written evidence_log.json file
    """
    print("\\n[Evidence Tracking] Writing evidence log...")
    
    # Collect all unique RAG entities used across all captions
    all_rag_entities = set()
    
    # Build clip evidence array
    clip_evidence = []
    
    # Create lookup for alignment scores by segment_id
    alignment_scores_lookup = {}
    for idx, score in enumerate(verified_output.preference_alignment_scores):
        if idx < len(verified_output.verified_reel_a):
            segment_id = verified_output.verified_reel_a[idx].segment_id
            alignment_scores_lookup[segment_id] = score
    
    # Process each verified event (use reel_a as primary, but track both captions)
    for idx, event_a in enumerate(verified_output.verified_reel_a):
        # Get corresponding reel_b event (same segment_id)
        event_b = None
        for eb in verified_output.verified_reel_b:
            if eb.segment_id == event_a.segment_id:
                event_b = eb
                break
        
        # Extract evidence from event_a (both reels should have same evidence sources)
        evidence = event_a.evidence if event_a.evidence else None
        
        if evidence:
            all_rag_entities.update(evidence.rag_facts)
            
            clip_entry = {
                "segment_id": event_a.segment_id,
                "event_type": event_a.event_type,
                "team": event_a.team,
                "players": evidence.d17_fields.get("players", []),
                "d15_fields": evidence.d15_fields,
                "d17_fields": evidence.d17_fields,
                "rag_entities_used": evidence.rag_facts,
                "rag_fact_texts": evidence.rag_fact_texts,
                "transcript_chunks": evidence.transcript_chunks,
                "prompt_used": evidence.prompt_used,
                "caption_reel_a": event_a.caption,
                "caption_reel_b": event_b.caption if event_b else None,
                "hallucination_check": "FAIL" if event_a.segment_id in [m.split(":")[0] for m in verified_output.unsupported_mentions] else "PASS",
                "unsupported_mentions": [m for m in verified_output.unsupported_mentions if m.startswith(event_a.segment_id)],
                "was_regenerated": event_a.was_regenerated,
                "original_caption": event_a.original_caption if event_a.was_regenerated else None,
                "alignment_score_reel_a": alignment_scores_lookup.get(event_a.segment_id, 0.0)
            }
            clip_evidence.append(clip_entry)
    
    # Build match recap evidence
    match_context_dict = {}
    if shared_state.match_context:
        match_context_dict = {
            "home_team": shared_state.match_context.home_team,
            "away_team": shared_state.match_context.away_team,
            "venue": shared_state.match_context.venue,
            "competition": shared_state.match_context.competition,
            "final_score": shared_state.match_context.final_score,
        }
    
    score_progression = []
    if shared_state.score_progression:
        score_progression = [
            {
                "time": sp.time,
                "scorer": sp.scorer,
                "team": sp.team,
                "score": sp.score
            }
            for sp in shared_state.score_progression
        ]
    
    match_recap_evidence = {
        "match_context": match_context_dict,
        "score_progression_used": score_progression,
        "recap_generated": shared_state.match_recap if hasattr(shared_state, 'match_recap') else None
    }
    
    # Build summary
    summary = {
        "total_clips": len(clip_evidence),
        "hallucination_flagged": verified_output.hallucination_flagged,
        "unsupported_mentions": verified_output.unsupported_mentions,
        "total_retries": verified_output.retry_count,
        "reel_a_alignment_score": verified_output.reel_a_alignment_score,
        "reel_b_alignment_score": verified_output.reel_b_alignment_score,
        "rag_entities_used": sorted(list(all_rag_entities))
    }
    
    # Build final evidence log
    evidence_log = {
        "match_name": match_name,
        "timestamp": datetime.now().isoformat(),
        "user_preference": user_preference,
        "clip_evidence": clip_evidence,
        "match_recap_evidence": match_recap_evidence,
        "summary": summary
    }
    
    # Write to file
    output_path.mkdir(parents=True, exist_ok=True)
    if perspective_name:
        filename = f"evidence_log_{perspective_name}.json"
    else:
        filename = "evidence_log.json"
    evidence_log_path = output_path / filename
    
    with open(evidence_log_path, 'w', encoding='utf-8') as f:
        json.dump(evidence_log, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Evidence log written: {evidence_log_path}")
    print(f"  - {len(clip_evidence)} clips tracked")
    print(f"  - {len(all_rag_entities)} unique RAG entities used")
    print(f"  - Hallucinations flagged: {verified_output.hallucination_flagged}")
    
    return evidence_log_path


def run_pipeline(match_name: str, user_preference: str, perspective_name: str = None) -> dict:
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
    
    # Start timing
    pipeline_start_time = time.time()
    
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
            
            # Stage 2a: Disagreement — filter low importance clips before caption generation
            print("\n[Stage 2a] Running disagreement analysis...")
            print("-" * 70)
            filtered_events, disagreement_log = run_disagreement(
                events=shared_state.events,
                shared_state=shared_state,
                provider=LLM_PROVIDER
            )
            shared_state.events = filtered_events
            shared_state.disagreement_log = disagreement_log
            print(f"✓ Disagreement complete: {len(filtered_events)} clips approved")
            print(f"  - Challenged: {len(disagreement_log)} clips")
            print(f"  - Overridden: {sum(1 for d in disagreement_log if d.outcome == 'overridden')} clips")
            
            print("\n[Stage 2b] Running fan_agent...")
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
            
            # Write evidence log
            match_output_path = OUTPUT_PATH / match_name
            write_evidence_log(
                match_name=match_name,
                user_preference=user_preference,
                shared_state=shared_state,
                verified_output=verified_output,
                output_path=match_output_path,
                perspective_name=perspective_name
            )
            
            # Write disagreement log
            if verified_output.disagreement_log:
                disagreement_log_path = match_output_path / f"disagreement_log_{perspective_name or 'default'}.json"
                with open(disagreement_log_path, 'w', encoding='utf-8') as f:
                    json.dump(
                        [d.dict() for d in verified_output.disagreement_log],
                        f, indent=2, ensure_ascii=False
                    )
                print(f"✓ Disagreement log saved: {disagreement_log_path}")
            
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
                "shared_state": shared_state,
                "verified_output": verified_output,
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
        # Stage 2a: Disagreement — Filter low importance clips before caption generation
        # ====================================================================
        print("\n[Stage 2a] Running disagreement analysis...")
        print("-" * 70)
        filtered_events, disagreement_log = run_disagreement(
            events=shared_state.events,
            shared_state=shared_state,
            provider=LLM_PROVIDER
        )
        shared_state.events = filtered_events
        shared_state.disagreement_log = disagreement_log
        print(f"✓ Stage 2a complete")
        print(f"  - Clips approved: {len(filtered_events)}")
        print(f"  - Clips challenged: {len(disagreement_log)}")
        print(f"  - Clips overridden: {sum(1 for d in disagreement_log if d.outcome == 'overridden')}")
        
        # ====================================================================
        # Stage 2b: Fan Agent (Executor)
        # ====================================================================
        print("\n[Stage 2b] Running fan_agent...")
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
        
        # Write evidence log
        match_output_path = OUTPUT_PATH / match_name
        write_evidence_log(
            match_name=match_name,
            user_preference=user_preference,
            shared_state=shared_state,
            verified_output=verified_output,
            output_path=match_output_path,
            perspective_name=perspective_name
        )
        
        # Write disagreement log
        if verified_output.disagreement_log:
            disagreement_log_path = match_output_path / f"disagreement_log_{perspective_name or 'default'}.json"
            with open(disagreement_log_path, 'w', encoding='utf-8') as f:
                json.dump(
                    [d.dict() for d in verified_output.disagreement_log],
                    f, indent=2, ensure_ascii=False
                )
            print(f"✓ Disagreement log saved: {disagreement_log_path}")
        
        # ====================================================================
        # Stage 4: Video Stitching
        # ====================================================================
        # Data sources for video stitching:
        # - Captions: From agent pipeline (verified_output.verified_reel_a/b)
        # - Timestamps: From agent pipeline (clip_start_sec, clip_end_sec in verified events)
        # This combines AI-generated captions with timestamps from D17 handoff data
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
        
        # Prepare Reel A events and captions
        reel_a_events_dict = []
        reel_a_events = []
        for event in verified_output.verified_reel_a:
            segment_id = event.segment_id
            clip_start = event.clip_start_sec
            clip_end = event.clip_end_sec
            
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
            clip_start = event.clip_start_sec
            clip_end = event.clip_end_sec
            
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
        
        # Save captions to JSON for easy access
        captions_output = {
            "match_name": match_name,
            "user_preference": user_preference,
            "hallucination_flagged": verified_output.hallucination_flagged,
            "retry_count": verified_output.retry_count,
            "reel_a_alignment_score": verified_output.reel_a_alignment_score,
            "reel_b_alignment_score": verified_output.reel_b_alignment_score,
            "evidence_summary": verified_output.evidence_summary,
            "reel_a_captions": [
                {
                    "segment_id": event.segment_id,
                    "event_type": event.event_type,
                    "caption": event.caption,
                    "clip_start_sec": event.clip_start_sec,
                    "clip_end_sec": event.clip_end_sec,
                    "evidence": {
                        "rag_facts": event.evidence.rag_facts if event.evidence else [],
                        "d15_fields": event.evidence.d15_fields if event.evidence else {},
                        "d17_fields": event.evidence.d17_fields if event.evidence else {},
                        "transcript_chunks": event.evidence.transcript_chunks if event.evidence else [],
                    } if event.evidence else None,
                }
                for event in verified_output.verified_reel_a
            ],
            "reel_b_captions": [
                {
                    "segment_id": event.segment_id,
                    "event_type": event.event_type,
                    "caption": event.caption,
                    "clip_start_sec": event.clip_start_sec,
                    "clip_end_sec": event.clip_end_sec,
                    "evidence": {
                        "rag_facts": event.evidence.rag_facts if event.evidence else [],
                        "d15_fields": event.evidence.d15_fields if event.evidence else {},
                        "d17_fields": event.evidence.d17_fields if event.evidence else {},
                        "transcript_chunks": event.evidence.transcript_chunks if event.evidence else [],
                    } if event.evidence else None,
                }
                for event in verified_output.verified_reel_b
            ],
        }
        
        captions_json_path = match_output_dir / "captions.json"
        with open(captions_json_path, 'w', encoding='utf-8') as f:
            json.dump(captions_output, f, indent=2, ensure_ascii=False)
        print(f"✓ Captions saved: {captions_json_path}")
        
        # End timing
        pipeline_end_time = time.time()
        pipeline_time_seconds = round(pipeline_end_time - pipeline_start_time, 2)
        print(f"\n[Pipeline] Total time: {pipeline_time_seconds:.2f}s")
        
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
            "pipeline_time_seconds": pipeline_time_seconds,
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
            "shared_state": shared_state,
            "verified_output": verified_output,
            "status": "success",
        }
    
    except FileNotFoundError as e:
        error_msg = f"File not found: {e}"
        print(f"\n✗ ERROR: {error_msg}")
        pipeline_end_time = time.time()
        pipeline_time_seconds = round(pipeline_end_time - pipeline_start_time, 2)
        print(f"\n[Pipeline] Total time: {pipeline_time_seconds:.2f}s")
        return {
            "reel_a_path": None,
            "reel_b_path": None,
            "reel_a_captions": [],
            "reel_b_captions": [],
            "hallucination_flagged": False,
            "pipeline_time_seconds": pipeline_time_seconds,
            "retry_count": 0,
            "status": "error",
            "error_message": error_msg,
        }
    
    except Exception as e:
        error_msg = f"Pipeline error: {type(e).__name__}: {e}"
        print(f"\n✗ ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        pipeline_end_time = time.time()
        pipeline_time_seconds = round(pipeline_end_time - pipeline_start_time, 2)
        print(f"\n[Pipeline] Total time: {pipeline_time_seconds:.2f}s")
        return {
            "reel_a_path": None,
            "reel_b_path": None,
            "reel_a_captions": [],
            "reel_b_captions": [],
            "hallucination_flagged": False,
            "retry_count": 0,
            "pipeline_time_seconds": pipeline_time_seconds,
            "status": "error",
            "error_message": error_msg,
        }


def run_pipeline_all_perspectives(match_name: str) -> dict:
    """
    Run the complete MGAI pipeline for ALL 3 perspectives automatically.
    Generates: Team A fan reel, Team B fan reel, and Neutral reel.
    
    Args:
        match_name: Unique identifier for the match (used in output filenames)
                   Example: "liverpool_2_0_man_city_2025_02_23"
    
    Returns:
        dict: Result dictionary containing:
            - team_a_reel_path (str): Path to Team A fan perspective MP4
            - team_b_reel_path (str): Path to Team B fan perspective MP4
            - neutral_reel_path (str): Path to neutral perspective MP4
            - team_a_name (str): Name of Team A
            - team_b_name (str): Name of Team B
            - status (str): "success" or "error"
            - error_message (str, optional): Error details if status is "error"
    """
    print("=" * 70)
    print("MGAI PIPELINE - 3-Perspective Reel Generation")
    print("=" * 70)
    print(f"Match: {match_name}")
    print("Generating all 3 perspectives: Team A, Team B, Neutral")
    print("=" * 70)
    
    try:
        # Load match data to extract team names
        d17_path = MOCK_DATA_PATH / match_name / "approach_b_dl_handoff.json"
        if not d17_path.exists():
            raise FileNotFoundError(f"D17 file not found: {d17_path}")
        
        with open(d17_path, 'r', encoding='utf-8') as f:
            d17_data = json.load(f)
        
        match_context = d17_data.get('match_context', {})
        home_team = match_context.get('home_team', 'Team A')
        away_team = match_context.get('away_team', 'Team B')
        
        print(f"\n🏟️  {home_team} (Home) vs {away_team} (Away)\n")
        
        # Normalize team names for filenames (lowercase, replace spaces with underscores)
        home_team_slug = home_team.lower().replace(' ', '_').replace('.', '').replace("'", "")
        away_team_slug = away_team.lower().replace(' ', '_').replace('.', '').replace("'", "")
        
        # ========================================================================
        # Run 1: Home Team Perspective
        # ========================================================================
        print(f"\n[Perspective 1/3] Generating {home_team} fan perspective...")
        print("-" * 70)
        result_home = run_pipeline(
            match_name=match_name,
            user_preference=f"I am a {home_team} fan",
            perspective_name=home_team_slug
        )
        
        if result_home['status'] != 'success':
            raise RuntimeError(f"{home_team} perspective failed: {result_home.get('error_message', 'Unknown error')}")
        
        # Rename home team reel
        match_output_dir = OUTPUT_PATH / match_name
        home_reel_path = match_output_dir / f"reel_{home_team_slug}.mp4"
        home_vtt_path = match_output_dir / f"reel_{home_team_slug}.vtt"
        neutral_reel_path = match_output_dir / "reel_neutral.mp4"
        neutral_vtt_path = match_output_dir / "reel_neutral.vtt"
        
        if Path(home_reel_path).exists():
            os.remove(home_reel_path)
        os.rename(result_home['reel_a_path'], str(home_reel_path))
        
        # Rename VTT files
        reel_a_vtt = match_output_dir / "reel_a.vtt"
        reel_b_vtt = match_output_dir / "reel_b.vtt"
        if reel_a_vtt.exists():
            if Path(home_vtt_path).exists():
                os.remove(home_vtt_path)
            os.rename(str(reel_a_vtt), str(home_vtt_path))
        if reel_b_vtt.exists():
            os.remove(str(reel_b_vtt))
        
        # Remove duplicate neutral reel generated as reel_b in the home run.
        if os.path.exists(result_home['reel_b_path']):
            os.remove(result_home['reel_b_path'])
        
        # Rename captions JSON
        captions_json = match_output_dir / "captions.json"
        home_captions_path = match_output_dir / f"captions_{home_team_slug}.json"
        
        if captions_json.exists():
            # Load and save only home team perspective captions (reel_a)
            with open(captions_json, 'r', encoding='utf-8') as f:
                captions_data = json.load(f)
            
            # Save home team captions (reel_a)
            home_captions_only = {
                "match_name": match_name,
                "perspective": f"{home_team} fan",
                "captions": captions_data.get("reel_a_captions", [])
            }
            with open(home_captions_path, 'w', encoding='utf-8') as f:
                json.dump(home_captions_only, f, indent=2, ensure_ascii=False)
            
            # Remove original combined file
            os.remove(str(captions_json))
        
        print(f"✓ {home_team} reel saved: {home_reel_path}")
        
        # ========================================================================
        # Run 2: Neutral Perspective
        # ========================================================================
        print(f"\n[Perspective 2/3] Generating Neutral perspective...")
        print("-" * 70)
        result_neutral = run_pipeline(
            match_name=match_name,
            user_preference="Neutral",
            perspective_name="neutral"
        )
        
        if result_neutral['status'] != 'success':
            raise RuntimeError(f"Neutral perspective failed: {result_neutral.get('error_message', 'Unknown error')}")
        
        # Rename neutral reel from dedicated neutral run (use reel_a as neutral output)
        if Path(neutral_reel_path).exists():
            os.remove(neutral_reel_path)
        os.rename(result_neutral['reel_a_path'], str(neutral_reel_path))
        
        # Rename neutral VTT file
        reel_a_vtt_neutral = match_output_dir / "reel_a.vtt"
        if reel_a_vtt_neutral.exists():
            if Path(neutral_vtt_path).exists():
                os.remove(neutral_vtt_path)
            os.rename(str(reel_a_vtt_neutral), str(neutral_vtt_path))
        
        # Save neutral captions from dedicated neutral run
        captions_json_neutral = match_output_dir / "captions.json"
        neutral_captions_path = match_output_dir / "captions_neutral.json"
        if captions_json_neutral.exists():
            with open(captions_json_neutral, 'r', encoding='utf-8') as f:
                captions_data = json.load(f)
            
            neutral_captions_only = {
                "match_name": match_name,
                "perspective": "Neutral",
                "captions": captions_data.get("reel_a_captions", [])
            }
            with open(neutral_captions_path, 'w', encoding='utf-8') as f:
                json.dump(neutral_captions_only, f, indent=2, ensure_ascii=False)
            
            os.remove(str(captions_json_neutral))
        
        # Remove duplicate neutral baseline outputs from neutral run
        if os.path.exists(result_neutral['reel_b_path']):
            os.remove(result_neutral['reel_b_path'])
        
        reel_b_vtt_neutral = match_output_dir / "reel_b.vtt"
        if reel_b_vtt_neutral.exists():
            os.remove(str(reel_b_vtt_neutral))
        
        print(f"✓ Neutral reel saved: {neutral_reel_path}")
        
        
        # ========================================================================
        # Run 3: Away Team Perspective
        # ========================================================================
        print(f"\n[Perspective 3/3] Generating {away_team} fan perspective...")
        print("-" * 70)
        result_away = run_pipeline(
            match_name=match_name,
            user_preference=f"I am a {away_team} fan",
            perspective_name=away_team_slug
        )
        
        if result_away['status'] != 'success':
            raise RuntimeError(f"{away_team} perspective failed: {result_away.get('error_message', 'Unknown error')}")
        
        # Rename away team reel, delete duplicate neutral
        away_reel_path = match_output_dir / f"reel_{away_team_slug}.mp4"
        away_vtt_path = match_output_dir / f"reel_{away_team_slug}.vtt"
        
        if Path(away_reel_path).exists():
            os.remove(away_reel_path)
        os.rename(result_away['reel_a_path'], str(away_reel_path))
        
        # Rename away team VTT file
        reel_a_vtt_away = match_output_dir / "reel_a.vtt"
        if reel_a_vtt_away.exists():
            if Path(away_vtt_path).exists():
                os.remove(away_vtt_path)
            os.rename(str(reel_a_vtt_away), str(away_vtt_path))
        
        # Rename away team captions JSON
        captions_json_away = match_output_dir / "captions.json"
        away_captions_path = match_output_dir / f"captions_{away_team_slug}.json"
        if captions_json_away.exists():
            # Load and save only reel_a (away team perspective)
            with open(captions_json_away, 'r', encoding='utf-8') as f:
                captions_data = json.load(f)
            
            away_captions_only = {
                "match_name": match_name,
                "perspective": f"{away_team} fan",
                "captions": captions_data.get("reel_a_captions", [])
            }
            with open(away_captions_path, 'w', encoding='utf-8') as f:
                json.dump(away_captions_only, f, indent=2, ensure_ascii=False)
            
            # Remove original combined file
            os.remove(str(captions_json_away))
        
        # Remove duplicate neutral reel from second run
        if os.path.exists(result_away['reel_b_path']):
            os.remove(result_away['reel_b_path'])
        
        # Remove duplicate neutral VTT from second run
        reel_b_vtt_away = match_output_dir / "reel_b.vtt"
        if reel_b_vtt_away.exists():
            os.remove(str(reel_b_vtt_away))
        
        print(f"✓ {away_team} reel saved: {away_reel_path}")
        
        # ========================================================================
        # Complete
        # ========================================================================
        print("\n" + "=" * 70)
        print("✅ ALL 3 PERSPECTIVES GENERATED")
        print("=" * 70)
        print(f"🏟️  {home_team} (Home):  {home_reel_path}")
        print(f"🏟️  {away_team} (Away):  {away_reel_path}")
        print(f"⚖️  Neutral:              {neutral_reel_path}")
        print("=" * 70)
        
        return {
            "team_a_reel_path": str(home_reel_path),
            "team_b_reel_path": str(away_reel_path),
            "neutral_reel_path": str(neutral_reel_path),
            "team_a_name": home_team,
            "team_b_name": away_team,
            "status": "success"
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            "team_a_reel_path": None,
            "team_b_reel_path": None,
            "neutral_reel_path": None,
            "team_a_name": None,
            "team_b_name": None,
            "status": "error",
            "error_message": error_msg
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
        default=None,
        help="User preference string for personalization (optional if --all-perspectives is used)"
    )
    parser.add_argument(
        "--all-perspectives",
        action="store_true",
        help="Generate all 3 perspectives automatically (Team A, Team B, Neutral)"
    )
    
    args = parser.parse_args()
    
    # Run pipeline based on mode
    if args.all_perspectives:
        # Generate all 3 perspectives automatically
        result = run_pipeline_all_perspectives(match_name=args.match_name)
        
        # Print result summary
        print("\n" + "=" * 70)
        print("PIPELINE RESULT")
        print("=" * 70)
        print(f"Status: {result['status']}")
        if result['status'] == 'success':
            print(f"{result['team_a_name']} Reel: {result['team_a_reel_path']}")
            print(f"{result['team_b_name']} Reel: {result['team_b_reel_path']}")
            print(f"Neutral Reel: {result['neutral_reel_path']}")
        else:
            print(f"Error: {result.get('error_message', 'Unknown error')}")
        print("=" * 70)
        
        sys.exit(0 if result['status'] == 'success' else 1)
    
    else:
        # Single perspective mode (original behavior)
        if not args.user_preference:
            args.user_preference = "I am an Arsenal fan and I love watching Saka play!"
            print(f"⚠️  No user preference provided, using default: {args.user_preference}")
        
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
        else:
            print(f"Error: {result.get('error_message', 'Unknown error')}")
        print(f"Hallucinations: {result['hallucination_flagged']}")
        print(f"Retries: {result['retry_count']}")
        print("=" * 70)
        
        # Exit with appropriate code
        sys.exit(0 if result['status'] == 'success' else 1)
