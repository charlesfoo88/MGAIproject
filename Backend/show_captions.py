"""
Quick script to display captions from all 3 perspectives by running the agents.
This is the proper way to get captions - directly from the agent output.
"""
import sys
from pathlib import Path

# Add Backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from State.shared_state import SharedState
from Agents import sports_analyst_agent, fan_agent

def get_captions_for_perspective(match_name, user_preference):
    """Run agents and extract captions for a given perspective."""
    shared_state = SharedState()
    shared_state.user_preference = user_preference
    
    # Run agents
    shared_state = sports_analyst_agent.run(shared_state)
    shared_state = fan_agent.run(shared_state)
    
    # Extract captions
    captions = []
    for event in shared_state.reel_a_events:
        captions.append({
            'segment_id': event.segment_id,
            'time': event.time,
            'event_type': event.event_type,
            'caption': event.caption,
        })
    
    return captions, shared_state.match_context

if __name__ == "__main__":
    match_name = "liverpool_2_0_man_city_2025_02_23"
    
    print("=" * 120)
    print("CAPTION COMPARISON - ALL 3 PERSPECTIVES")
    print("=" * 120)
    print()
    
    # Get Liverpool fan perspective
    print("Generating Liverpool fan perspective...")
    liv_captions, match_ctx = get_captions_for_perspective(match_name, "I am a Liverpool fan")
    
    # Get Man City fan perspective
    print("Generating Manchester City fan perspective...")
    mc_captions, _ = get_captions_for_perspective(match_name, "I am a Manchester City fan")
    
    # Get Neutral perspective  
    print("Generating Neutral perspective...")
    shared_state_neutral = SharedState()
    shared_state_neutral.user_preference = "Neutral"
    shared_state_neutral = sports_analyst_agent.run(shared_state_neutral)
    shared_state_neutral = fan_agent.run(shared_state_neutral)
    neu_captions = []
    for event in shared_state_neutral.reel_b_events:  # Neutral uses reel_b
        neu_captions.append({
            'segment_id': event.segment_id,
            'time': event.time,
            'event_type': event.event_type,
            'caption': event.caption,
        })
    
    print()
    print("=" * 120)
    print(f"Match: {match_ctx.home_team} vs {match_ctx.away_team}")
    print("=" * 120)
    print()
    
    # Print table header
    print(f"{'Event':<6} | {'Liverpool Fan':<75} | {'Man City Fan':<75} | {'Neutral':<75}")
    print("-" * 6 + "|" + "-" * 77 + "|" + "-" * 77 + "|" + "-" * 77)
    
    # Print each event's captions side by side
    for i in range(max(len(liv_captions), len(mc_captions), len(neu_captions))):
        liv_cap = liv_captions[i]['caption'] if i < len(liv_captions) else ""
        mc_cap = mc_captions[i]['caption'] if i < len(mc_captions) else ""
        neu_cap = neu_captions[i]['caption'] if i < len(neu_captions) else ""
        
        # Truncate if too long
        liv_cap = (liv_cap[:72] + "...") if len(liv_cap) > 75 else liv_cap
        mc_cap = (mc_cap[:72] + "...") if len(mc_cap) > 75 else mc_cap
        neu_cap = (neu_cap[:72] + "...") if len(neu_cap) > 75 else neu_cap
        
        print(f"{i+1:<6} | {liv_cap:<75} | {mc_cap:<75} | {neu_cap:<75}")
    
    print("-" * 6 + "|" + "-" * 77 + "|" + "-" * 77 + "|" + "-" * 77)
    print()
    print(f"Total events: Liverpool={len(liv_captions)}, Man City={len(mc_captions)}, Neutral={len(neu_captions)}")
    print("=" * 120)
