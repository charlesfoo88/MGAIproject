"""
MGAI Pipeline Evaluation Script

Runs the pipeline multiple times with different user preferences and logs results.
"""

# =============================================================================
# PRE-APPROVED DEMO INPUT TEXTS (Liverpool 2-0 Man City)
# =============================================================================
# These preferences are pre-tested and should be used for demo and evaluation.
# They are designed to work well with query transformation in Sports Analyst Agent.
#
# Match name: liverpool_2_0_man_city_2024_12_01
#
# 1. Liverpool fan (team preference):
#    "I am a Liverpool fan and I love watching the Reds play at Anfield"
#    → extracts: team=Liverpool, search=[Liverpool, Anfield, Reds]
#
# 2. Manchester City fan (team preference):
#    "I support Manchester City and I follow the Citizens closely"
#    → extracts: team=Manchester City, search=[Manchester City, Citizens]
#
# 3. Neutral viewer (no team preference):
#    "I am a neutral viewer and I want to see all the goals from this match"
#    → extracts: team=null, search=[goals, neutral]
#
# 4. Player preference (Salah):
#    "I love watching Mohamed Salah play for Liverpool, he is my favourite player"
#    → extracts: team=Liverpool, players=[Mohamed Salah]
#
# 5. Player preference (Gakpo):
#    "Cody Gakpo is my favourite Liverpool player and I love watching him score"
#    → extracts: team=Liverpool, players=[Cody Gakpo]
#
# For self-consistency checks: use inputs 1 and 4 (run 3x each)
# For disagreement analysis: use all 5 inputs
# For demo: type these inputs live in the UI free text field
# =============================================================================

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Setup paths for relative imports
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

# Import pipeline and config
from pipeline import run_pipeline
from config import ACTIVE_MATCH, MOCK_DATA_PATH, OUTPUT_PATH

# Import embedding tool for similarity calculations
from Tools.embedding_tool import encode, cosine_similarity

# Match name (constant for all tests)
MATCH_NAME = "liverpool_2_0_man_city_2024_12_01"


def run_evaluation():
    """Run pipeline evaluation with multiple user preferences."""
    
    print("=" * 80)
    print("MGAI PIPELINE EVALUATION")
    print("=" * 80)
    print(f"\nMatch: {MATCH_NAME}")
    
    # Load preferences dynamically from evaluation_config.json
    config = generate_evaluation_config(MATCH_NAME)
    preferences = (config["auto_generated"]["disagreement_preferences"] + 
                   config["user_defined"]["disagreement_preferences"])
    
    print(f"Test preferences: {len(preferences)}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "=" * 80 + "\n")
    
    results = []
    
    # Run pipeline for each preference
    for i, preference in enumerate(preferences, 1):
        print(f"[Test {i}/{len(preferences)}] Running pipeline...")
        print(f"Preference: {preference}")
        print("-" * 80)
        
        # Time the pipeline execution
        start_time = time.time()
        
        try:
            result = run_pipeline(
                match_name=MATCH_NAME,
                user_preference=preference
            )
            
            end_time = time.time()
            time_taken = end_time - start_time
            
            # Extract metrics
            test_result = {
                "test_number": i,
                "preference": preference,
                "hallucination_flagged": result.get("hallucination_flagged", False),
                "retry_count": result.get("retry_count", 0),
                "reel_a_alignment_score": result.get("reel_a_alignment_score", 0.0),
                "reel_b_alignment_score": result.get("reel_b_alignment_score", 0.0),
                "reel_a_clip_count": len(result.get("reel_a_captions", [])),
                "reel_b_clip_count": len(result.get("reel_b_captions", [])),
                "time_seconds": round(time_taken, 2),
                "status": result.get("status", "unknown"),
            }
            
            results.append(test_result)
            
            print(f"✓ Completed in {time_taken:.2f}s")
            print(f"  Hallucination flagged: {test_result['hallucination_flagged']}")
            print(f"  Retry count: {test_result['retry_count']}")
            print(f"  Reel A alignment: {test_result['reel_a_alignment_score']:.3f}")
            print(f"  Reel B alignment: {test_result['reel_b_alignment_score']:.3f}")
            print(f"  Reel A clips: {test_result['reel_a_clip_count']}")
            print(f"  Reel B clips: {test_result['reel_b_clip_count']}")
            print()
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
            
            # Record error
            test_result = {
                "test_number": i,
                "preference": preference,
                "hallucination_flagged": False,
                "retry_count": 0,
                "reel_a_alignment_score": 0.0,
                "reel_b_alignment_score": 0.0,
                "reel_a_clip_count": 0,
                "reel_b_clip_count": 0,
                "time_seconds": 0.0,
                "status": "error",
                "error": str(e),
            }
            results.append(test_result)
            print()
    
    # Print results table
    print("\n" + "=" * 80)
    print("EVALUATION RESULTS")
    print("=" * 80 + "\n")
    
    print_results_table(results)
    
    # Compute and print averages
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80 + "\n")
    
    print_summary_statistics(results)
    
    # Save results to JSON
    output_path = backend_dir / "Outputs" / ACTIVE_MATCH / "evaluation_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    evaluation_data = {
        "match_name": MATCH_NAME,
        "test_count": len(preferences),
        "timestamp": datetime.now().isoformat(),
        "results": results,
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(evaluation_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Results saved to: {output_path}")
    print("\n" + "=" * 80)


def print_results_table(results):
    """Print formatted results table."""
    
    # Table header
    header = f"{'#':<3} | {'Preference':<50} | {'Hall.':<6} | {'Retry':<5} | {'A Score':<8} | {'B Score':<8} | {'A Clips':<7} | {'B Clips':<7} | {'Time(s)':<8}"
    separator = "-" * len(header)
    
    print(header)
    print(separator)
    
    # Table rows
    for result in results:
        # Truncate preference if too long
        pref_short = result['preference'][:47] + "..." if len(result['preference']) > 50 else result['preference']
        
        row = (
            f"{result['test_number']:<3} | "
            f"{pref_short:<50} | "
            f"{'Yes' if result['hallucination_flagged'] else 'No':<6} | "
            f"{result['retry_count']:<5} | "
            f"{result['reel_a_alignment_score']:.3f}{'':<4} | "
            f"{result['reel_b_alignment_score']:.3f}{'':<4} | "
            f"{result['reel_a_clip_count']:<7} | "
            f"{result['reel_b_clip_count']:<7} | "
            f"{result['time_seconds']:<8.2f}"
        )
        print(row)
    
    print(separator)


def print_summary_statistics(results):
    """Compute and print summary statistics."""
    
    # Filter successful runs
    successful_results = [r for r in results if r['status'] != 'error']
    
    if not successful_results:
        print("No successful runs to compute statistics.")
        return
    
    # Compute averages
    total_runs = len(successful_results)
    hallucination_count = sum(1 for r in successful_results if r['hallucination_flagged'])
    hallucination_rate = (hallucination_count / total_runs) * 100
    
    avg_retry_count = sum(r['retry_count'] for r in successful_results) / total_runs
    avg_reel_a_alignment = sum(r['reel_a_alignment_score'] for r in successful_results) / total_runs
    avg_reel_b_alignment = sum(r['reel_b_alignment_score'] for r in successful_results) / total_runs
    avg_reel_a_clips = sum(r['reel_a_clip_count'] for r in successful_results) / total_runs
    avg_reel_b_clips = sum(r['reel_b_clip_count'] for r in successful_results) / total_runs
    avg_time = sum(r['time_seconds'] for r in successful_results) / total_runs
    
    # Print statistics
    print(f"Successful runs: {total_runs}/{len(results)}")
    print(f"\nHallucination Detection:")
    print(f"  Hallucination rate: {hallucination_rate:.1f}% ({hallucination_count}/{total_runs})")
    print(f"  Average retry count: {avg_retry_count:.2f}")
    
    print(f"\nAlignment Scores:")
    print(f"  Average Reel A alignment: {avg_reel_a_alignment:.3f}")
    print(f"  Average Reel B alignment: {avg_reel_b_alignment:.3f}")
    
    print(f"\nClip Counts:")
    print(f"  Average Reel A clips: {avg_reel_a_clips:.1f}")
    print(f"  Average Reel B clips: {avg_reel_b_clips:.1f}")
    
    print(f"\nPerformance:")
    print(f"  Average execution time: {avg_time:.2f} seconds")


# =============================================================================
# NEW EVALUATION FUNCTIONS FOR RUBRIC REQUIREMENTS
# =============================================================================

def run_self_consistency_check(
    match_name: str,
    preferences: list,
    runs: int = 3
) -> dict:
    """
    Run self-consistency check by running pipeline multiple times with same input.
    
    Args:
        match_name: Match identifier
        preferences: List of preference strings to test
        runs: Number of times to run each preference (default: 3)
        
    Returns:
        Dictionary with consistency scores per preference
    """
    print("\n" + "=" * 80)
    print("SELF-CONSISTENCY CHECK")
    print("=" * 80)
    print(f"Testing {len(preferences)} preferences × {runs} runs each\n")
    
    results_per_preference = []
    
    for pref_idx, preference in enumerate(preferences, 1):
        print(f"[{pref_idx}/{len(preferences)}] Testing: {preference[:60]}...")
        
        run_captions = []
        
        # Run pipeline multiple times with same preference
        for run_num in range(runs):
            print(f"  Run {run_num + 1}/{runs}...", end=" ")
            try:
                result = run_pipeline(
                    match_name=match_name,
                    user_preference=preference
                )
                captions = result.get("reel_a_captions", [])
                run_captions.append(captions)
                print(f"✓ ({len(captions)} captions)")
            except Exception as e:
                print(f"✗ Error: {e}")
                run_captions.append([])
        
        # Compute pairwise similarity between caption sets
        pairwise_scores = []
        
        if len(run_captions) >= 2:
            # For each pair of runs, compute average caption similarity
            for i in range(len(run_captions)):
                for j in range(i + 1, len(run_captions)):
                    captions_i = run_captions[i]
                    captions_j = run_captions[j]
                    
                    # Match captions by index (same clip position)
                    min_len = min(len(captions_i), len(captions_j))
                    if min_len > 0:
                        caption_similarities = []
                        for k in range(min_len):
                            emb_i = encode(captions_i[k])
                            emb_j = encode(captions_j[k])
                            sim = cosine_similarity(emb_i, emb_j)
                            caption_similarities.append(sim)
                        
                        avg_sim = sum(caption_similarities) / len(caption_similarities)
                        pairwise_scores.append(avg_sim)
        
        mean_consistency = sum(pairwise_scores) / len(pairwise_scores) if pairwise_scores else 0.0
        is_consistent = mean_consistency > 0.75
        
        result_entry = {
            "preference": preference,
            "run_captions": run_captions,
            "pairwise_similarity_scores": pairwise_scores,
            "mean_consistency_score": round(mean_consistency, 3),
            "is_consistent": is_consistent
        }
        
        results_per_preference.append(result_entry)
        
        print(f"  Mean consistency: {mean_consistency:.3f} ({'✓ PASS' if is_consistent else '✗ FAIL'})\n")
    
    return {
        "preferences_tested": len(preferences),
        "runs_per_preference": runs,
        "results": results_per_preference,
        "overall_consistency_rate": sum(1 for r in results_per_preference if r["is_consistent"]) / len(results_per_preference) if results_per_preference else 0.0
    }


def run_cross_modal_agreement_check(
    match_name: str
) -> dict:
    """
    Check agreement between Gemini Vision timestamps and API-Football match minutes.
    
    Args:
        match_name: Match identifier
        
    Returns:
        Dictionary with cross-modal agreement analysis
    """
    print("\n" + "=" * 80)
    print("CROSS-MODAL AGREEMENT CHECK")
    print("=" * 80)
    print(f"Match: {match_name}\n")
    
    # Load extraction_report.json
    report_path = OUTPUT_PATH / match_name / "extraction_report.json"
    
    if not report_path.exists():
        report_path = Path(__file__).resolve().parent / "Outputs" / match_name / "extraction_report.json"
    
    if not report_path.exists():
        print(f"✗ Error: extraction_report.json not found at {report_path}")
        return {
            "error": "extraction_report.json not found",
            "total_events_checked": 0
        }
    
    with open(report_path, 'r', encoding='utf-8') as f:
        extraction_report = json.load(f)
    
    # Estimate video duration from max timestamp
    all_timestamps = []
    for event in extraction_report.get("mapped_events", []):
        if event.get("video_timestamp_seconds"):
            all_timestamps.append(event["video_timestamp_seconds"])
    
    video_duration = max(all_timestamps) if all_timestamps else 600  # default 10 min
    print(f"Estimated video duration: {video_duration:.0f} seconds ({video_duration/60:.1f} minutes)\n")
    
    events_checked = []
    
    for event in extraction_report.get("mapped_events", []):
        if not event.get("found") or not event.get("video_timestamp_seconds"):
            continue
        
        player = event.get("player", "Unknown")
        event_type = event.get("event_type", "unknown")
        match_minute = int(event.get("match_minute", "0"))
        gemini_timestamp = event.get("video_timestamp_seconds", 0)
        
        # Expected timestamp: (match_minute / 90) * video_duration
        # Assuming 90 min match maps linearly to video duration
        expected_timestamp = (match_minute / 90.0) * video_duration
        
        deviation = abs(gemini_timestamp - expected_timestamp)
        agreement = "high" if deviation < 60 else "low"
        
        event_check = {
            "player": player,
            "event_type": event_type,
            "match_minute": match_minute,
            "gemini_timestamp": gemini_timestamp,
            "expected_timestamp": round(expected_timestamp, 1),
            "deviation_seconds": round(deviation, 1),
            "agreement": agreement
        }
        
        events_checked.append(event_check)
        
        print(f"{event_type.upper()} - {player} @ {match_minute}'")
        print(f"  Gemini: {gemini_timestamp}s | Expected: {expected_timestamp:.0f}s | Deviation: {deviation:.0f}s [{agreement.upper()}]")
    
    # Compute summary statistics
    total_checked = len(events_checked)
    high_agreement = sum(1 for e in events_checked if e["agreement"] == "high")
    low_agreement = sum(1 for e in events_checked if e["agreement"] == "low")
    mean_deviation = sum(e["deviation_seconds"] for e in events_checked) / total_checked if total_checked > 0 else 0.0
    
    print(f"\n✓ Checked {total_checked} events")
    print(f"  High agreement (< 60s): {high_agreement}")
    print(f"  Low agreement (>= 60s): {low_agreement}")
    print(f"  Mean deviation: {mean_deviation:.1f} seconds")
    
    return {
        "total_events_checked": total_checked,
        "events": events_checked,
        "mean_deviation_seconds": round(mean_deviation, 1),
        "high_agreement_count": high_agreement,
        "low_agreement_count": low_agreement
    }


def run_disagreement_analysis(
    match_name: str,
    preferences: list
) -> dict:
    """
    Analyze how different preferences lead to different captions for same clips.
    
    Args:
        match_name: Match identifier
        preferences: List of preference strings to test
        
    Returns:
        Dictionary with disagreement analysis per clip
    """
    print("\n" + "=" * 80)
    print("DISAGREEMENT ANALYSIS")
    print("=" * 80)
    print(f"Testing {len(preferences)} different preferences\n")
    
    # Run pipeline once for each preference
    all_runs = []
    
    for pref_idx, preference in enumerate(preferences, 1):
        print(f"[{pref_idx}/{len(preferences)}] Running: {preference[:60]}...")
        try:
            result = run_pipeline(
                match_name=match_name,
                user_preference=preference
            )
            
            reel_a_captions = result.get("reel_a_captions", [])
            reel_a_events = result.get("reel_a_events", [])
            
            all_runs.append({
                "preference": preference,
                "captions": reel_a_captions,
                "events": reel_a_events
            })
            
            print(f"  ✓ Generated {len(reel_a_captions)} captions\n")
        except Exception as e:
            print(f"  ✗ Error: {e}\n")
            all_runs.append({
                "preference": preference,
                "captions": [],
                "events": []
            })
    
    # Analyze per-clip disagreement
    # Assume all runs have same number of clips (in same order)
    max_clips = max(len(run["captions"]) for run in all_runs) if all_runs else 0
    
    per_clip_disagreement = []
    
    for clip_idx in range(max_clips):
        # Collect all captions for this clip across preferences
        captions_by_preference = {}
        segment_id = None
        event_type = None
        
        for run in all_runs:
            if clip_idx < len(run["captions"]):
                captions_by_preference[run["preference"][:50]] = run["captions"][clip_idx]
                
                if clip_idx < len(run["events"]):
                    segment_id = run["events"][clip_idx].get("segment_id", f"clip_{clip_idx}")
                    event_type = run["events"][clip_idx].get("event_type", "unknown")
        
        # Compute pairwise similarity between all caption pairs
        caption_list = list(captions_by_preference.values())
        
        if len(caption_list) >= 2:
            pairwise_sims = []
            
            for i in range(len(caption_list)):
                for j in range(i + 1, len(caption_list)):
                    emb_i = encode(caption_list[i])
                    emb_j = encode(caption_list[j])
                    sim = cosine_similarity(emb_i, emb_j)
                    pairwise_sims.append(sim)
            
            mean_sim = sum(pairwise_sims) / len(pairwise_sims) if pairwise_sims else 1.0
            disagreement_rate = 1.0 - mean_sim
            high_disagreement = mean_sim < 0.6
            
            clip_analysis = {
                "segment_id": segment_id or f"clip_{clip_idx}",
                "event_type": event_type or "unknown",
                "captions_by_preference": captions_by_preference,
                "mean_pairwise_similarity": round(mean_sim, 3),
                "disagreement_rate": round(disagreement_rate, 3),
                "high_disagreement": high_disagreement
            }
            
            per_clip_disagreement.append(clip_analysis)
    
    overall_disagreement = sum(c["disagreement_rate"] for c in per_clip_disagreement) / len(per_clip_disagreement) if per_clip_disagreement else 0.0
    
    print(f"✓ Analyzed {len(per_clip_disagreement)} clips")
    print(f"  Overall disagreement rate: {overall_disagreement:.3f}")
    print(f"  High disagreement clips: {sum(1 for c in per_clip_disagreement if c['high_disagreement'])}")
    
    return {
        "preferences_tested": len(preferences),
        "clips_analysed": len(per_clip_disagreement),
        "per_clip_disagreement": per_clip_disagreement,
        "overall_disagreement_rate": round(overall_disagreement, 3)
    }


def run_verifier_analysis(
    match_name: str,
    preferences: list
) -> dict:
    """
    Analyze Critic Agent (verifier model) effectiveness across multiple runs.
    
    Args:
        match_name: Match identifier
        preferences: List of preference strings to test
        
    Returns:
        Dictionary with verifier effectiveness analysis
    """
    print("\n" + "=" * 80)
    print("VERIFIER MODEL ANALYSIS")
    print("=" * 80)
    print(f"Testing Critic Agent with {len(preferences)} preferences\n")
    
    per_run_results = []
    
    for pref_idx, preference in enumerate(preferences, 1):
        print(f"[{pref_idx}/{len(preferences)}] Running: {preference[:60]}...")
        try:
            result = run_pipeline(
                match_name=match_name,
                user_preference=preference
            )
            
            hallucination_flagged = result.get("hallucination_flagged", False)
            retry_count = result.get("retry_count", 0)
            reel_a_alignment = result.get("reel_a_alignment_score", 0.0)
            reel_b_alignment = result.get("reel_b_alignment_score", 0.0)
            status = result.get("status", "unknown")
            pipeline_time = result.get("pipeline_time_seconds", 0.0)
            
            run_result = {
                "preference": preference,
                "hallucination_flagged": hallucination_flagged,
                "retry_count": retry_count,
                "reel_a_alignment_score": reel_a_alignment,
                "reel_b_alignment_score": reel_b_alignment,
                "pipeline_time_seconds": pipeline_time,
                "status": status
            }
            
            per_run_results.append(run_result)
            
            print(f"  Hallucination: {'Yes' if hallucination_flagged else 'No'} | Retries: {retry_count} | Status: {status}\n")
            
        except Exception as e:
            print(f"  ✗ Error: {e}\n")
            per_run_results.append({
                "preference": preference,
                "hallucination_flagged": False,
                "retry_count": 0,
                "reel_a_alignment_score": 0.0,
                "reel_b_alignment_score": 0.0,
                "status": "error"
            })
    
    # Compute summary statistics
    total_runs = len(per_run_results)
    successful_runs = [r for r in per_run_results if r["status"] == "success"]
    
    hallucinations_detected = sum(1 for r in per_run_results if r["hallucination_flagged"])
    total_retries = sum(r["retry_count"] for r in per_run_results)
    
    # Retry effectiveness: resolved if hallucination was flagged, retries were used, and final status is success
    resolved_count = sum(1 for r in per_run_results if r["hallucination_flagged"] and r["retry_count"] > 0 and r["status"] == "success")
    retry_effectiveness = "resolved" if resolved_count > 0 else "not_applicable"
    
    avg_reel_a = sum(r["reel_a_alignment_score"] for r in successful_runs) / len(successful_runs) if successful_runs else 0.0
    avg_reel_b = sum(r["reel_b_alignment_score"] for r in successful_runs) / len(successful_runs) if successful_runs else 0.0
    avg_time = round(sum(r.get("pipeline_time_seconds", 0) for r in per_run_results) / len(per_run_results), 2) if per_run_results else 0.0
    
    hallucination_rate = (hallucinations_detected / total_runs) if total_runs > 0 else 0.0
    
    print(f"✓ Completed {total_runs} runs")
    print(f"  Hallucinations detected: {hallucinations_detected}")
    print(f"  Total retries: {total_retries}")
    print(f"  Retry effectiveness: {retry_effectiveness}")
    print(f"  Avg Reel A alignment: {avg_reel_a:.3f}")
    print(f"  Avg Reel B alignment: {avg_reel_b:.3f}")
    print(f"  Avg pipeline time: {avg_time:.2f}s")
    
    return {
        "total_runs": total_runs,
        "hallucination_rate": round(hallucination_rate, 3),
        "total_hallucinations_detected": hallucinations_detected,
        "total_retries": total_retries,
        "retry_effectiveness": retry_effectiveness,
        "avg_reel_a_alignment": round(avg_reel_a, 3),
        "avg_reel_b_alignment": round(avg_reel_b, 3),
        "avg_pipeline_time_seconds": avg_time,
        "per_run_results": per_run_results
    }


def generate_evaluation_config(match_name: str) -> dict:
    """
    Auto-generate evaluation config from dl_handoff.json.
    
    Args:
        match_name: Match identifier
        
    Returns:
        Evaluation config dictionary
    """
    print(f"\n[Evaluation Config] Generating for {match_name}...")
    
    # Load dl_handoff.json
    dl_handoff_path = MOCK_DATA_PATH / match_name / "approach_b_dl_handoff.json"
    
    if not dl_handoff_path.exists():
        print(f"✗ Error: {dl_handoff_path} not found")
        # Return default config
        config = {
            "match": match_name,
            "auto_generated": {
                "consistency_preferences": [],
                "disagreement_preferences": []
            },
            "user_defined": {
                "consistency_preferences": [],
                "disagreement_preferences": []
            },
            "self_consistency_runs": 3
        }
        return config
    
    with open(dl_handoff_path, 'r', encoding='utf-8') as f:
        dl_handoff = json.load(f)
    
    # Extract teams
    match_context = dl_handoff.get("match_context", {})
    home_team = match_context.get("home_team", "Team A")
    away_team = match_context.get("away_team", "Team B")
    
    # Extract goal scorers
    goal_scorers = []
    for event in dl_handoff.get("events", []):
        if event.get("event_type") in ["goal", "penalty_goal"]:
            if "scorer" in event:
                goal_scorers.append(event["scorer"])
            elif event.get("players"):
                goal_scorers.append(event["players"][0])
    
    # Remove duplicates, keep order
    unique_scorers = []
    for scorer in goal_scorers:
        if scorer not in unique_scorers:
            unique_scorers.append(scorer)
    
    # Generate preferences
    consistency_prefs = [
        f"I am a {home_team} fan and I love watching {home_team} play",
        f"I support {away_team} and I follow {away_team} closely"
    ]
    
    disagreement_prefs = [
        f"I am a {home_team} fan and I love watching {home_team} play",
        f"I support {away_team} and I follow {away_team} closely",
        "I am a neutral viewer and I want to see all the goals from this match"
    ]
    
    # Add player-specific preferences for top 2 scorers
    # Look up which team each scorer belongs to from events
    for scorer in unique_scorers[:2]:
        # Find scorer's team from events
        scorer_team = home_team  # default to home team
        for event in dl_handoff.get("events", []):
            if event.get("scorer") == scorer:
                scorer_team = event.get("team", home_team)
                break
            # Also check players list
            if scorer in event.get("players", []):
                scorer_team = event.get("team", home_team)
                break
        disagreement_prefs.append(
            f"I love watching {scorer} play for {scorer_team}, he is my favourite player"
        )
    
    config = {
        "match": match_name,
        "auto_generated": {
            "consistency_preferences": consistency_prefs,
            "disagreement_preferences": disagreement_prefs
        },
        "user_defined": {
            "consistency_preferences": [],
            "disagreement_preferences": []
        },
        "self_consistency_runs": 3
    }
    
    # Save config
    output_path = OUTPUT_PATH / match_name / "evaluation_config.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Config saved: {output_path}")
    
    return config


def run_full_evaluation(match_name: str = None):
    """
    Run full evaluation including all 4 analysis types.
    
    Args:
        match_name: Match identifier (uses ACTIVE_MATCH if None)
    """
    if match_name is None:
        match_name = ACTIVE_MATCH
    
    print("=" * 80)
    print("MGAI FULL EVALUATION SUITE")
    print("=" * 80)
    print(f"Match: {match_name}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Generate or load evaluation config
    config = generate_evaluation_config(match_name)
    
    # Combine auto-generated + user-defined preferences
    consistency_prefs = config["auto_generated"]["consistency_preferences"] + config["user_defined"]["consistency_preferences"]
    disagreement_prefs = config["auto_generated"]["disagreement_preferences"] + config["user_defined"]["disagreement_preferences"]
    
    # Run all 4 analyses
    print("\n" + "=" * 80)
    print("RUNNING 4 EVALUATION ANALYSES")
    print("=" * 80)
    
    # 1. Self-consistency check
    self_consistency_results = run_self_consistency_check(
        match_name=match_name,
        preferences=consistency_prefs[:2],  # Limit to 2 for speed
        runs=config["self_consistency_runs"]
    )
    
    # 2. Cross-modal agreement check
    cross_modal_results = run_cross_modal_agreement_check(match_name)
    
    # 3. Disagreement analysis
    disagreement_results = run_disagreement_analysis(
        match_name=match_name,
        preferences=disagreement_prefs
    )
    
    # 4. Verifier analysis
    verifier_results = run_verifier_analysis(
        match_name=match_name,
        preferences=disagreement_prefs
    )
    
    # Combine results
    full_results = {
        "match_name": match_name,
        "timestamp": datetime.now().isoformat(),
        "self_consistency": self_consistency_results,
        "cross_modal_agreement": cross_modal_results,
        "disagreement_analysis": disagreement_results,
        "verifier_analysis": verifier_results
    }
    
    # Save results
    output_path = OUTPUT_PATH / match_name / "full_evaluation_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(full_results, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "=" * 80)
    print("FULL EVALUATION SUMMARY")
    print("=" * 80)
    print(f"\nSelf-Consistency:")
    print(f"  Overall consistency rate: {self_consistency_results.get('overall_consistency_rate', 0):.1%}")
    
    print(f"\nCross-Modal Agreement:")
    print(f"  Mean deviation: {cross_modal_results.get('mean_deviation_seconds', 0):.1f}s")
    print(f"  High agreement: {cross_modal_results.get('high_agreement_count', 0)}/{cross_modal_results.get('total_events_checked', 0)}")
    
    print(f"\nDisagreement Analysis:")
    print(f"  Overall disagreement rate: {disagreement_results.get('overall_disagreement_rate', 0):.1%}")
    
    print(f"\nVerifier Analysis:")
    print(f"  Hallucination rate: {verifier_results.get('hallucination_rate', 0):.1%}")
    print(f"  Total retries: {verifier_results.get('total_retries', 0)}")
    
    print(f"\n✓ Full results saved to: {output_path}")
    print("=" * 80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MGAI Pipeline Evaluation")
    parser.add_argument('--full', action='store_true')
    
    args = parser.parse_args()
    
    if args.full:
        run_full_evaluation()
    else:
        run_evaluation()
