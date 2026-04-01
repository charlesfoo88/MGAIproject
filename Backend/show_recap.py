"""Quick script to display the match recap from last test"""
import sys
from pathlib import Path

# Add Backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from State.shared_state import SharedState
from Agents import sports_analyst_agent, fan_agent

# Initialize
shared_state = SharedState()
shared_state.user_preference = "I am an Arsenal fan"

print("Running pipeline to generate match recap...")
print("=" * 70)

# Run stages
shared_state = sports_analyst_agent.run(shared_state)
shared_state = fan_agent.run(shared_state)

print("\n" + "=" * 70)
print("MATCH RECAP")
print("=" * 70)
print(f"\n{shared_state.match_recap}\n")
print("=" * 70)
print(f"Length: {len(shared_state.match_recap)} characters")
