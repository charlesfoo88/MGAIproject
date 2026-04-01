"""
Test script to demonstrate search_terms integration with RAG enrichment.
Compares old behavior (single entity) vs new behavior (multiple search terms).
"""

import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from Agents.sports_analyst_agent import transform_query, enrich_events_with_rag
from Schemas import HandoffEvent, DLHandoff
from config import LLM_PROVIDER, D17_MOCK_DATA

def test_search_terms_rag():
    """Test RAG enrichment with transformed search terms"""
    
    # Load actual mock events from D17
    with open(D17_MOCK_DATA, 'r', encoding='utf-8') as f:
        d17_data = json.load(f)
        dl_handoff = DLHandoff(**d17_data)
        mock_events = dl_handoff.events[:3]  # Use first 3 events
    
    print("=" * 70)
    print("TEST: RAG Enrichment with Search Terms")
    print("=" * 70)
    print()
    
    # Test Case 1: Single entity (old behavior)
    print("Case 1: Single entity preference")
    print("-" * 70)
    user_pref_1 = "I am an Arsenal fan"
    print(f"User preference: '{user_pref_1}'")
    print()
    
    transformed_1 = transform_query(user_pref_1, provider=LLM_PROVIDER)
    search_terms_1 = transformed_1.get('search_terms', [])
    print(f"Search terms extracted: {search_terms_1}")
    
    rag_context_1 = enrich_events_with_rag(mock_events, "Arsenal", search_terms_1)
    fact_count_1 = len(rag_context_1.split('\n\n')) if rag_context_1 else 0
    print(f"RAG facts retrieved: {fact_count_1}")
    print()
    print()
    
    # Test Case 2: Multiple entities (new behavior - shows benefit)
    print("Case 2: Multiple entity preference")
    print("-" * 70)
    user_pref_2 = "I love Arsenal, especially Saka and Martinelli"
    print(f"User preference: '{user_pref_2}'")
    print()
    
    transformed_2 = transform_query(user_pref_2, provider=LLM_PROVIDER)
    search_terms_2 = transformed_2.get('search_terms', [])
    print(f"Search terms extracted: {search_terms_2}")
    
    rag_context_2 = enrich_events_with_rag(mock_events, "Arsenal", search_terms_2)
    fact_count_2 = len(rag_context_2.split('\n\n')) if rag_context_2 else 0
    print(f"RAG facts retrieved: {fact_count_2}")
    print()
    print()
    
    # Test Case 3: Player-only preference (demonstrates null team handling)
    print("Case 3: Player-only preference")
    print("-" * 70)
    user_pref_3 = "I support Saka and Martinelli"
    print(f"User preference: '{user_pref_3}'")
    print()
    
    transformed_3 = transform_query(user_pref_3, provider=LLM_PROVIDER)
    search_terms_3 = transformed_3.get('search_terms', [])
    preferred_team_3 = transformed_3.get('preferred_team')
    print(f"Preferred team: {preferred_team_3}")
    print(f"Search terms extracted: {search_terms_3}")
    
    rag_context_3 = enrich_events_with_rag(mock_events, preferred_team_3, search_terms_3)
    fact_count_3 = len(rag_context_3.split('\n\n')) if rag_context_3 else 0
    print(f"RAG facts retrieved: {fact_count_3}")
    print()
    
    print("=" * 70)
    print("KEY BENEFIT: Query transformation extracts multiple entities,")
    print("enabling RAG to retrieve facts for all mentioned entities,")
    print("not just the first match from regex extraction.")
    print("=" * 70)


if __name__ == "__main__":
    test_search_terms_rag()
