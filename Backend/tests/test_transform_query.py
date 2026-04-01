"""
Test script for transform_query() function in Sports Analyst Agent.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from Agents.sports_analyst_agent import transform_query
from config import LLM_PROVIDER

def test_transform_query():
    """Test transform_query with various user preferences"""
    
    test_cases = [
        "I am an Arsenal fan and I love Saka",
        "I support Martinelli AND Odegaard",
        "Manchester City all the way",
        "I love Haaland",
        "Liverpool fan here, especially Salah and Nunez",
        "I'm a Chelsea supporter",
    ]
    
    print("=" * 70)
    print("TESTING transform_query() FUNCTION")
    print("=" * 70)
    print(f"Using LLM Provider: {LLM_PROVIDER}")
    print()
    
    for i, user_pref in enumerate(test_cases, 1):
        print(f"Test {i}:")
        print(f"  Input: '{user_pref}'")
        
        try:
            result = transform_query(user_pref, provider=LLM_PROVIDER)
            print(f"  Output:")
            print(f"    preferred_team: {result.get('preferred_team')}")
            print(f"    preferred_players: {result.get('preferred_players')}")
            print(f"    search_terms: {result.get('search_terms')}")
        except Exception as e:
            print(f"  ERROR: {e}")
        
        print()
    
    print("=" * 70)
    print("Testing complete!")
    print("=" * 70)


if __name__ == "__main__":
    test_transform_query()
