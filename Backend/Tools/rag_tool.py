"""
RAG Tool - Structured knowledge base lookup for entity fact retrieval.

Provides fact retrieval for entity mentions in video captions to reduce
hallucinations and add contextual information to highlight generation.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

# Handle both module import and direct execution
try:
    from ..config import KNOWLEDGE_BASE_PATH
except ImportError:
    # Direct execution - add parent directory to path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from config import KNOWLEDGE_BASE_PATH


# Global cache for knowledge base
_knowledge_base: Optional[Dict[str, Any]] = None


def load_knowledge_base() -> Dict[str, Any]:
    """
    Load structured knowledge base from JSON file into memory.

    The KB is cached for fast subsequent lookups.

    Returns:
        Dict[str, Any]: Structured knowledge base with sections (teams, players, stadiums, etc.)
    """
    global _knowledge_base

    if _knowledge_base is not None:
        return _knowledge_base

    try:
        with open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as f:
            _knowledge_base = json.load(f)
        
        if not isinstance(_knowledge_base, dict):
            print(f"[WARN] Knowledge base at {KNOWLEDGE_BASE_PATH} is not a JSON object. Using empty dict.")
            _knowledge_base = {}
        else:
            print(f"[OK] Knowledge base loaded: {len(_knowledge_base)} top-level sections")
        
        return _knowledge_base
    
    except FileNotFoundError:
        print(f"[WARN] Knowledge base not found at {KNOWLEDGE_BASE_PATH}")
        _knowledge_base = {}
        return _knowledge_base
    
    except json.JSONDecodeError as e:
        print(f"[WARN] Knowledge base JSON is malformed at {KNOWLEDGE_BASE_PATH}: {e}")
        _knowledge_base = {}
        return _knowledge_base


def _normalize(text: str) -> str:
    """Normalize text for case-insensitive matching."""
    return text.strip().lower()


def _extract_fact(entry: Any) -> str:
    """
    Extract a human-readable fact from a KB entry.
    """
    if isinstance(entry, str):
        return entry.strip()

    if not isinstance(entry, dict):
        return ""

    # Try common description fields
    for field in ("description", "summary", "fact", "details"):
        value = entry.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def _get_candidates(entry_key: str, entry_value: Any) -> list[str]:
    """
    Build list of candidate names/aliases to match against query.
    """
    candidates = [entry_key]

    if isinstance(entry_value, dict):
        # Add primary name
        for field in ("name", "label"):
            value = entry_value.get(field)
            if isinstance(value, str) and value.strip():
                candidates.append(value.strip())

        # Add aliases
        aliases = entry_value.get("aliases")
        if isinstance(aliases, list):
            candidates.extend(
                alias for alias in aliases 
                if isinstance(alias, str) and alias.strip()
            )

    return candidates


def lookup(entity_name: str) -> str:
    """
    Look up an entity in the structured knowledge base.

    Searches across all sections (teams, players, stadiums, competitions, matches)
    and matches against entity names and aliases.

    The KB structure is:
    {
        "teams": {"arsenal": {"name": "Arsenal", "aliases": ["Gunners"], "description": "..."}},
        "players": {"bukayo_saka": {"name": "Bukayo Saka", "aliases": ["Saka"], "description": "..."}},
        "stadiums": {...},
        "competitions": {...},
        "matches": {...}
    }

    Args:
        entity_name: The entity name to search for (e.g., "Arsenal", "Saka", "Gunners")

    Returns:
        str: Description string if entity is found, empty string if not found
    """
    kb = load_knowledge_base()
    query = _normalize(entity_name)
    
    if not query or not isinstance(kb, dict):
        return ""

    # Define sections to search (in order of priority)
    sections = ["teams", "players", "stadiums", "competitions", "matches", "event_types"]
    
    # Search through each section
    for section_name in sections:
        section = kb.get(section_name)
        
        # Skip if section doesn't exist or is not a dict
        if not isinstance(section, dict):
            continue
        
        # Search through entries in this section
        for entry_key, entry_value in section.items():
            if not isinstance(entry_value, dict):
                continue
            
            # Check if query matches the entry's name (case-insensitive)
            entry_name = entry_value.get("name", "")
            if isinstance(entry_name, str) and _normalize(entry_name) == query:
                description = entry_value.get("description", "")
                if description:
                    print(f"[OK] Found fact for '{entity_name}'")
                    return description
            
            # Check if query matches any alias (case-insensitive)
            aliases = entry_value.get("aliases", [])
            if isinstance(aliases, list):
                for alias in aliases:
                    if isinstance(alias, str) and _normalize(alias) == query:
                        description = entry_value.get("description", "")
                        if description:
                            print(f"[OK] Found fact for '{entity_name}'")
                            return description

    print(f"[MISS] No fact found for '{entity_name}'")
    return ""


def reset_cache():
    """
    Reset the knowledge base cache (useful for testing or hot-reload).
    """
    global _knowledge_base
    _knowledge_base = None
    print("Knowledge base cache reset")


# Test harness
if __name__ == "__main__":
    # Force fresh load
    reset_cache()
    
    # Prepare output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path(__file__).resolve().parent.parent / "tests" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    output_file = results_dir / f"rag_test_result_{timestamp}.txt"
    
    # Capture output
    output_lines = []
    
    def print_and_save(text=""):
        """Print to console and save to output list"""
        print(text)
        output_lines.append(text)
    
    print_and_save("=" * 60)
    print_and_save("RAG Tool - Knowledge Base Lookup Test")
    print_and_save("=" * 60)
    print_and_save()
    print_and_save(f"Loading from: {KNOWLEDGE_BASE_PATH}")
    print_and_save()

    # Test 1: Load knowledge base
    print_and_save("[Test 1] Loading knowledge base...")
    kb = load_knowledge_base()
    print_and_save(f"Sections: {list(kb.keys())}")
    print_and_save()

    # Test 2: Team name match
    print_and_save("[Test 2] 'Arsenal' → should find by name")
    result = lookup("Arsenal")
    status = "✓" if result else "✗"
    print_and_save(f"{status} Found: {bool(result)}")
    if result:
        print_and_save(f"   Description: {result[:80]}...")
    print_and_save()

    # Test 3: Team alias match
    print_and_save("[Test 3] 'Gunners' → should find by alias")
    result = lookup("Gunners")
    status = "✓" if result else "✗"
    print_and_save(f"{status} Found: {bool(result)}")
    if result:
        print_and_save(f"   Description: {result[:80]}...")
    print_and_save()

    # Test 4: Player alias match
    print_and_save("[Test 4] 'Saka' → should find by alias")
    result = lookup("Saka")
    status = "✓" if result else "✗"
    print_and_save(f"{status} Found: {bool(result)}")
    if result:
        print_and_save(f"   Description: {result[:80]}...")
    print_and_save()

    # Test 5: Stadium alias match
    print_and_save("[Test 5] 'Wembley' → should find by alias")
    result = lookup("Wembley")
    status = "✓" if result else "✗"
    print_and_save(f"{status} Found: {bool(result)}")
    if result:
        print_and_save(f"   Description: {result[:80]}...")
    print_and_save()

    # Test 6: Team alias match (alternate)
    print_and_save("[Test 6] 'Man City' → should find by alias")
    result = lookup("Man City")
    status = "✓" if result else "✗"
    print_and_save(f"{status} Found: {bool(result)}")
    if result:
        print_and_save(f"   Description: {result[:80]}...")
    print_and_save()

    # Test 7: Unknown entity
    print_and_save("[Test 7] 'Unknown Player' → should return empty string")
    result = lookup("Unknown Player")
    status = "✓" if not result else "✗"
    print_and_save(f"{status} Not found (expected): {not bool(result)}")
    print_and_save()

    # Test 8: Cache test (multiple lookups)
    print_and_save("[Test 8] Cache test (multiple lookups)")
    for entity in ["Arsenal", "Saka", "Gunners"]:
        result = lookup(entity)
        print_and_save(f"  {entity}: {len(result)} chars")
    print_and_save()

    # Test 9: Test newly added match players
    new_players = ["De Bruyne", "Martinelli", "Walker", "Trossard", "Rodri"]
    print_and_save("[Test 9] Testing newly added match players...")
    for player in new_players:
        result = lookup(player)
        status = "✓" if result else "✗"
        print_and_save(f"  {status} {player}: {'Found' if result else 'NOT FOUND'} {f'({len(result)} chars)' if result else ''}")
    print_and_save()

    print_and_save("=" * 60)
    print_and_save("All tests completed!")
    print_and_save("=" * 60)
    
    # Save results to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    print()
    print(f"📄 Test results saved to: {output_file}")
    print(f"   Timestamp: {timestamp}")

