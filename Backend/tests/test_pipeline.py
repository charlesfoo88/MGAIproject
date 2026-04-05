"""Direct pipeline test - no batch wrapper needed"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Setup paths
backend_dir = Path(__file__).parent.parent  # Go up one level from tests/ to Backend/
sys.path.insert(0, str(backend_dir))

# Import ACTIVE_MATCH from config
from config import ACTIVE_MATCH

# Setup result logging - organized by match
results_dir = Path(__file__).parent / "results" / ACTIVE_MATCH  # tests/results/{ACTIVE_MATCH}/
results_dir.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
result_file = results_dir / f"test_result_{timestamp}.txt"

# Capture both stdout and write to file
class TeeOutput:
    def __init__(self, file_path):
        self.terminal = sys.stdout
        self.log = open(file_path, 'w', encoding='utf-8')
    
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
    
    def flush(self):
        self.terminal.flush()
        self.log.flush()
    
    def isatty(self):
        """Required by sentence_transformers library"""
        return self.terminal.isatty() if hasattr(self.terminal, 'isatty') else False
    
    def close(self):
        self.log.close()

# Start logging
tee = TeeOutput(result_file)
sys.stdout = tee

# Suppress warnings
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("MGAI Agent Pipeline Test")
print("=" * 70)

# Import and test
print("\n[Setup] Loading modules...")
from State.shared_state import SharedState
from Agents import sports_analyst_agent, fan_agent, critic_agent
from config import ALIGNMENT_THRESHOLD

# Initialize shared state
shared_state = SharedState()
shared_state.user_preference = "I am an Arsenal fan and I love watching Saka play!"
print(f"✓ User preference: {shared_state.user_preference}")

print("\n[Stage 1] Running sports_analyst_agent...")
print("-" * 70)
try:
    shared_state = sports_analyst_agent.run(shared_state)
    print(f"✓ Filtered {len(shared_state.events)} events")
    print(f"✓ Preferred entity: {shared_state.preferred_entity}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[Stage 2] Running fan_agent...")
print("-" * 70)
try:
    shared_state = fan_agent.run(shared_state)
    print(f"✓ Reel A (Personalized): {len(shared_state.reel_a_events)} clips")
    print(f"✓ Reel B (Neutral): {len(shared_state.reel_b_events)} clips")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[Stage 3] Running critic_agent...")
print("-" * 70)
try:
    verified_output = critic_agent.run(shared_state)
    print(f"✓ Verification complete")
    print(f"✓ Hallucinations flagged: {verified_output.hallucination_flagged}")
    print(f"✓ Total retries: {verified_output.retry_count}/2")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[Results] Final Verified Captions:")
print("-" * 70)
print("\nReel A (Arsenal/Saka highlights):")
for i, event in enumerate(verified_output.verified_reel_a, 1):
    print(f"\n{i}. [{event.clip_start_sec:.1f}s - {event.clip_end_sec:.1f}s]")
    print(f"   Type: {event.event_type}, Team: {event.team}")
    print(f"   Caption: {event.caption}")

print("\n" + "-" * 70)
print("\nReel B (Neutral highlights):")
for i, event in enumerate(verified_output.verified_reel_b, 1):
    print(f"\n{i}. [{event.clip_start_sec:.1f}s - {event.clip_end_sec:.1f}s]")
    print(f"   Type: {event.event_type}, Team: {event.team}")
    print(f"   Caption: {event.caption}")

print("\n" + "=" * 70)
print("[Alignment Scores] Preference Alignment Summary:")
print("=" * 70)
print(f"Reel A (Personalized) Alignment: {verified_output.reel_a_alignment_score:.3f}")
print(f"  Threshold: {ALIGNMENT_THRESHOLD}")
print(f"  Quality: {'✓ GOOD' if verified_output.reel_a_alignment_score >= ALIGNMENT_THRESHOLD else '⚠ LOW'}")
print(f"\nReel B (Neutral) Alignment: {verified_output.reel_b_alignment_score:.3f}")
print(f"  Note: Neutral captions are not expected to align with user preference")
print(f"\nIndividual Scores:")
reel_a_count = len(verified_output.verified_reel_a)
for i, score in enumerate(verified_output.preference_alignment_scores, 1):
    reel_label = "Reel A" if i <= reel_a_count else "Reel B"
    event_idx = i if i <= reel_a_count else i - reel_a_count
    print(f"  {reel_label}[{event_idx}]: {score:.3f}")

# Display evidence tracing
if verified_output.evidence_summary:
    print("\n" + "=" * 70)
    print("Evidence Tracing Summary:")
    print("=" * 70)
    summary = verified_output.evidence_summary
    print(f"Total captions traced: {summary.get('total_captions')}")
    print(f"RAG entities used: {', '.join(summary.get('rag_entities_used', []))}")
    print(f"D15 fields used: {', '.join(summary.get('d15_fields_used', []))}")
    print(f"D17 fields used: {', '.join(summary.get('d17_fields_used', []))}")
    print()
    print("Per-caption evidence (Reel A):")
    for i, event in enumerate(verified_output.verified_reel_a, 1):
        if event.evidence:
            print(f"  [{i}] RAG facts: {event.evidence.rag_facts}")
            print(f"       D17 narrative: {str(event.evidence.d17_fields.get('narrative', ''))[:60]}...")
            print(f"       Importance: {event.evidence.d15_fields.get('importance_score')}")

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED!")
print("=" * 70)

# Close log file and show path
tee.close()
sys.stdout = tee.terminal
print(f"\n📝 Test results saved to: {result_file}")
print(f"   Timestamp: {timestamp}")

