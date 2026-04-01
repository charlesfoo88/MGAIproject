"""
MGAI Pipeline Evaluation Script

Runs the pipeline multiple times with different user preferences and logs results.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Setup paths for relative imports
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

# Import pipeline
from pipeline import run_pipeline

# Test preferences
TEST_PREFERENCES = [
    "I am an Arsenal fan and I love watching Saka play",
    "I support Manchester City and Haaland is my favourite player",
    "I am a neutral viewer interested in all goals",
    "I love watching Saka and Martinelli play for Arsenal",
    "I am a Manchester City fan and I follow De Bruyne closely",
]

# Match name (constant for all tests)
MATCH_NAME = "arsenal_vs_city_efl_2026"


def run_evaluation():
    """Run pipeline evaluation with multiple user preferences."""
    
    print("=" * 80)
    print("MGAI PIPELINE EVALUATION")
    print("=" * 80)
    print(f"\nMatch: {MATCH_NAME}")
    print(f"Test preferences: {len(TEST_PREFERENCES)}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "=" * 80 + "\n")
    
    results = []
    
    # Run pipeline for each preference
    for i, preference in enumerate(TEST_PREFERENCES, 1):
        print(f"[Test {i}/{len(TEST_PREFERENCES)}] Running pipeline...")
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
    output_path = backend_dir / "Outputs" / "evaluation_results.json"
    output_path.parent.mkdir(exist_ok=True)
    
    evaluation_data = {
        "match_name": MATCH_NAME,
        "test_count": len(TEST_PREFERENCES),
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


if __name__ == "__main__":
    run_evaluation()
