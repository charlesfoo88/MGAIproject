"""
Sports Analyst Agent - Stage 1: Planner

Loads highlight candidates and handoff data, filters events based on confidence
and importance thresholds, extracts user preferences, enriches events with RAG
context, and prepares structured input for the Fan Agent.
"""

import json
import re
from typing import List, Optional
from pathlib import Path

# Relative imports
try:
    from ..config import (
        DEMO_MODE,
        D15_MOCK_DATA,
        D17_MOCK_DATA,
        D15_FILE_PATH,
        D17_FILE_PATH,
        MIN_CONFIDENCE,
        IMPORTANCE_THRESHOLD,
        LLM_PROVIDER,
        GROQ_API_KEY,
        GEMINI_API_KEY,
        GROQ_MODEL,
        GEMINI_MODEL,
    )
    from ..State import SharedState
    from ..Schemas import (
        HighlightCandidate,
        HandoffEvent,
        MatchContext,
        EntityRegistry,
        ScoreProgression,
        AgentInput,
        DLHandoff,
    )
    from ..Tools import lookup as rag_lookup
except ImportError:
    # Direct execution fallback
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from config import (
        DEMO_MODE,
        D15_MOCK_DATA,
        D17_MOCK_DATA,
        D15_FILE_PATH,
        D17_FILE_PATH,
        MIN_CONFIDENCE,
        IMPORTANCE_THRESHOLD,
        LLM_PROVIDER,
        GROQ_API_KEY,
        GEMINI_API_KEY,
        GROQ_MODEL,
        GEMINI_MODEL,
    )
    from State import SharedState
    from Schemas import (
        HighlightCandidate,
        HandoffEvent,
        MatchContext,
        EntityRegistry,
        ScoreProgression,
        AgentInput,
        DLHandoff,
    )
    from Tools import lookup as rag_lookup


# Import LLM providers
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("⚠ Groq library not available")

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠ Google Generative AI library not available")


def extract_preferred_entity(user_preference: str) -> Optional[str]:
    """
    Extract the preferred team/player from user preference string.
    
    Examples:
        "I am an Arsenal fan" -> "Arsenal"
        "I support Manchester City" -> "Manchester City"
        "I love Saka" -> "Saka"
    
    Args:
        user_preference: User preference text
        
    Returns:
        Extracted entity name, or None if not found
    """
    if not user_preference:
        return None
    
    # Common patterns to match
    patterns = [
        r"(?:I am an?|I'm an?)\s+([A-Z][a-zA-Z\s]+?)\s+fan",
        r"(?:I support|I love|I like)\s+([A-Z][a-zA-Z\s]+?)(?:\s|$|\.)",
        r"(?:fan of|supporter of)\s+([A-Z][a-zA-Z\s]+?)(?:\s|$|\.)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, user_preference)
        if match:
            entity = match.group(1).strip()
            # Clean up common suffixes
            entity = re.sub(r'\s+(team|club|football)$', '', entity, flags=re.IGNORECASE)
            return entity
    
    # Fallback: extract any capitalized words (team/player names)
    words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', user_preference)
    if words:
        return words[0]
    
    return None


def transform_query(user_preference: str, provider: str = "groq") -> dict:
    """
    Transform raw user preference into structured search terms using LLM.
    
    This function uses LLM to extract:
    - preferred_team: Primary team mentioned (str or null)
    - preferred_players: List of player names mentioned (list of str)
    - search_terms: Additional search terms (list of str)
    
    If LLM parsing fails, falls back to extract_preferred_entity() for basic extraction.
    
    Args:
        user_preference: Raw user preference text
        provider: LLM provider to use ("groq" or "gemini")
        
    Returns:
        Dict with keys: preferred_team, preferred_players, search_terms
        
    Examples:
        Input: "I love Arsenal and Saka"
        Output: {
            "preferred_team": "Arsenal",
            "preferred_players": ["Saka"],
            "search_terms": ["Arsenal", "Saka"]
        }
        
        Input: "I support Martinelli AND Odegaard"
        Output: {
            "preferred_team": null,
            "preferred_players": ["Martinelli", "Odegaard"],
            "search_terms": ["Martinelli", "Odegaard"]
        }
    """
    if not user_preference:
        return {
            "preferred_team": None,
            "preferred_players": [],
            "search_terms": []
        }
    
    # Build LLM prompt for JSON extraction
    prompt = f"""Extract soccer/football entities from the user preference below.

User preference: "{user_preference}"

Respond ONLY with valid JSON in this exact format (no preamble, no explanation):
{{
  "preferred_team": "Team Name" or null,
  "preferred_players": ["Player1", "Player2"] or [],
  "search_terms": ["term1", "term2"] or []
}}

Rules:
- preferred_team: Extract the primary team mentioned (e.g., "Arsenal", "Manchester City")
- preferred_players: Extract all player names mentioned (list of strings)
- search_terms: Include all teams and players as search terms
- If only players mentioned (no team), set preferred_team to null
- Use proper capitalization for names
- Return valid JSON only, no additional text"""

    try:
        # Call LLM based on provider
        if provider == "groq":
            if not GROQ_AVAILABLE:
                raise ValueError("Groq library not available")
            client = Groq(api_key=GROQ_API_KEY)
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Lower temperature for structured extraction
                max_tokens=200,
            )
            llm_output = response.choices[0].message.content.strip()
        elif provider == "gemini":
            if not GEMINI_AVAILABLE:
                raise ValueError("Gemini library not available")
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel(GEMINI_MODEL)
            response = model.generate_content(prompt)
            llm_output = response.text.strip()
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        # Parse JSON response
        # Clean up markdown code blocks if present
        if llm_output.startswith("```json"):
            llm_output = llm_output.replace("```json", "").replace("```", "").strip()
        elif llm_output.startswith("```"):
            llm_output = llm_output.replace("```", "").strip()
        
        transformed = json.loads(llm_output)
        
        # Validate structure
        if not isinstance(transformed, dict):
            raise ValueError("LLM response is not a dict")
        
        # Ensure required keys exist with defaults
        result = {
            "preferred_team": transformed.get("preferred_team"),
            "preferred_players": transformed.get("preferred_players", []),
            "search_terms": transformed.get("search_terms", [])
        }
        
        # Validate types
        if result["preferred_players"] is None:
            result["preferred_players"] = []
        if result["search_terms"] is None:
            result["search_terms"] = []
        
        if not isinstance(result["preferred_players"], list):
            result["preferred_players"] = []
        if not isinstance(result["search_terms"], list):
            result["search_terms"] = []
        
        print(f"✓ Query transformed: {result}")
        return result
        
    except Exception as e:
        print(f"⚠ Query transformation failed ({e}), using fallback extraction")
        
        # Fallback to basic regex extraction
        preferred_entity = extract_preferred_entity(user_preference)
        
        fallback_result = {
            "preferred_team": preferred_entity if preferred_entity else None,
            "preferred_players": [],
            "search_terms": [preferred_entity] if preferred_entity else []
        }
        
        print(f"✓ Fallback extraction: {fallback_result}")
        return fallback_result


def load_data_files(demo_mode: bool = True):
    """
    Load D15 and D17 JSON data files.
    
    Args:
        demo_mode: If True, load mock data. If False, load real pipeline data.
        
    Returns:
        Tuple of (highlight_candidates, dl_handoff_data)
    """
    # Determine which files to load
    d15_path = D15_MOCK_DATA if demo_mode else D15_FILE_PATH
    d17_path = D17_MOCK_DATA if demo_mode else D17_FILE_PATH
    
    print(f"Loading D15 from: {d15_path}")
    print(f"Loading D17 from: {d17_path}")
    
    # Load D15 highlight candidates
    with open(d15_path, 'r', encoding='utf-8') as f:
        d15_data = json.load(f)
        highlight_candidates = [HighlightCandidate(**item) for item in d15_data]
    
    # Load D17 handoff data
    with open(d17_path, 'r', encoding='utf-8') as f:
        d17_data = json.load(f)
        dl_handoff = DLHandoff(**d17_data)
    
    print(f"✓ Loaded {len(highlight_candidates)} highlight candidates")
    print(f"✓ Loaded {len(dl_handoff.events)} handoff events")
    
    return highlight_candidates, dl_handoff


def filter_events(
    events: List[HandoffEvent],
    min_confidence: float,
    importance_threshold: float
) -> List[HandoffEvent]:
    """
    Filter events based on confidence and importance thresholds.
    
    Args:
        events: List of HandoffEvent objects
        min_confidence: Minimum confidence score (0.0-1.0)
        importance_threshold: Minimum importance score (0.0-1.0)
        
    Returns:
        Filtered list of events
    """
    filtered = [
        event for event in events
        if event.confidence >= min_confidence and event.importance >= importance_threshold
    ]
    
    print(f"Filtered {len(events)} events -> {len(filtered)} events")
    print(f"  (confidence >= {min_confidence}, importance >= {importance_threshold})")
    
    return filtered


def enrich_events_with_rag(events: List[HandoffEvent], preferred_entity: Optional[str] = None, search_terms: List[str] = []) -> str:
    """
    Enrich events by looking up team facts from the knowledge base.
    
    Args:
        events: List of HandoffEvent objects
        preferred_entity: User's preferred team/player (optional)
        search_terms: Additional search terms from query transformation (optional)
        
    Returns:
        Combined RAG context string with facts about relevant entities
    """
    rag_facts = []
    seen_entities = set()
    
    # Add preferred entity fact first (if specified)
    if preferred_entity:
        fact = rag_lookup(preferred_entity)
        if fact:
            rag_facts.append(f"[{preferred_entity}] {fact}")
            seen_entities.add(preferred_entity.lower())
    
    # Look up additional search terms from query transformation
    for term in search_terms:
        if term.lower() not in seen_entities:
            fact = rag_lookup(term)
            if fact:
                rag_facts.append(f"[{term}] {fact}")
                seen_entities.add(term.lower())
    
    # Look up facts for teams mentioned in events
    for event in events:
        if event.team and event.team.lower() not in seen_entities:
            fact = rag_lookup(event.team)
            if fact:
                rag_facts.append(f"[{event.team}] {fact}")
                seen_entities.add(event.team.lower())
        
        # Look up player facts
        for player in event.players:
            if player.lower() not in seen_entities:
                fact = rag_lookup(player)
                if fact:
                    rag_facts.append(f"[{player}] {fact}")
                    seen_entities.add(player.lower())
    
    rag_context = "\n\n".join(rag_facts) if rag_facts else ""
    
    if rag_context:
        print(f"✓ Retrieved {len(rag_facts)} facts from knowledge base")
    else:
        print("⚠ No RAG facts found for events")
    
    return rag_context


def build_transcript_context(events: List[HandoffEvent]) -> str:
    """
    Build transcript context by combining event narratives.
    
    Args:
        events: List of HandoffEvent objects
        
    Returns:
        Combined transcript context string
    """
    transcripts = []
    
    for event in events:
        timestamp = event.time
        narrative = event.context.narrative if hasattr(event.context, 'narrative') else ""
        
        if narrative:
            transcripts.append(f"[{timestamp}] {narrative}")
    
    transcript_context = "\n".join(transcripts)
    
    print(f"✓ Built transcript context: {len(transcripts)} narrative entries")
    
    return transcript_context


def run(shared_state: SharedState) -> SharedState:
    """
    Sports Analyst Agent - Main execution function.
    
    Stage 1: Load data, filter events, extract preferences, enrich with RAG,
    and prepare AgentInput for the Fan Agent.
    
    Args:
        shared_state: SharedState object containing user preferences
        
    Returns:
        Updated SharedState with populated agent input data
    """
    print("=" * 70)
    print("SPORTS ANALYST AGENT - Stage 1: Planner")
    print("=" * 70)
    print()
    
    # Step 1: Load data files
    print("[Step 1] Loading data files...")
    highlight_candidates, dl_handoff = load_data_files(demo_mode=DEMO_MODE)
    print()
    
    # Step 2: Extract preferred entity from user preference
    print("[Step 2] Extracting user preference...")
    preferred_entity = extract_preferred_entity(shared_state.user_preference)
    if preferred_entity:
        print(f"✓ Preferred entity: {preferred_entity}")
        shared_state.preferred_entity = preferred_entity
    else:
        print("⚠ No preferred entity extracted from user preference")
        print(f"  User preference: '{shared_state.user_preference}'")
    print()
    
    # Step 2b: Transform query using LLM for structured extraction
    print("[Step 2b] Transforming query with LLM...")
    query_transformed = transform_query(shared_state.user_preference, provider=LLM_PROVIDER)
    shared_state.query_transformed = query_transformed
    if query_transformed.get("preferred_team"):
        print(f"  Team: {query_transformed['preferred_team']}")
    if query_transformed.get("preferred_players"):
        print(f"  Players: {', '.join(query_transformed['preferred_players'])}")
    if query_transformed.get("search_terms"):
        print(f"  Search terms: {', '.join(query_transformed['search_terms'])}")
    print()
    
    # Step 3: Filter events
    print("[Step 3] Filtering events...")
    filtered_events = filter_events(
        dl_handoff.events,
        MIN_CONFIDENCE,
        IMPORTANCE_THRESHOLD
    )
    print()
    
    # Step 4: Enrich with RAG context
    print("[Step 4] Enriching with knowledge base facts...")
    # Use transformed search terms for better RAG matching
    search_terms = shared_state.query_transformed.get('search_terms', []) if shared_state.query_transformed else []
    rag_context = enrich_events_with_rag(filtered_events, preferred_entity, search_terms)
    print()
    
    # Step 5: Build transcript context
    print("[Step 5] Building transcript context...")
    transcript_context = build_transcript_context(filtered_events)
    print()
    
    # Step 6: Build AgentInput
    print("[Step 6] Building AgentInput...")
    agent_input = AgentInput(
        match_id=dl_handoff.match_context.match_id,
        home_team=dl_handoff.match_context.home_team,
        away_team=dl_handoff.match_context.away_team,
        competition=dl_handoff.match_context.competition,
        venue=dl_handoff.match_context.venue,
        preferred_entity=preferred_entity or "",
        events=filtered_events,
        score_progression=dl_handoff.score_progression,
        entity_registry=dl_handoff.entity_registry,
        transcript_context=transcript_context,
        rag_context=rag_context,
    )
    
    print(f"✓ AgentInput created:")
    print(f"    Match: {agent_input.home_team} vs {agent_input.away_team}")
    print(f"    Competition: {agent_input.competition}")
    print(f"    Venue: {agent_input.venue}")
    print(f"    Preferred entity: {agent_input.preferred_entity}")
    print(f"    Events: {len(agent_input.events)}")
    print(f"    Transcript chunks: {len(agent_input.transcript_context.split(chr(10)))}")
    print(f"    RAG facts: {len(agent_input.rag_context.split(chr(10) * 2)) if agent_input.rag_context else 0}")
    print()
    
    # Step 7: Update shared state
    print("[Step 7] Updating shared state...")
    shared_state.events = filtered_events
    shared_state.highlight_candidates = highlight_candidates
    shared_state.match_context = dl_handoff.match_context
    shared_state.entity_registry = dl_handoff.entity_registry
    shared_state.score_progression = dl_handoff.score_progression
    print("✓ SharedState updated")
    print()
    
    print("=" * 70)
    print("✓ SPORTS ANALYST AGENT COMPLETE")
    print("=" * 70)
    print()
    
    return shared_state


# Test harness
if __name__ == "__main__":
    print("Testing Sports Analyst Agent")
    print()
    
    # Create test shared state
    test_state = SharedState()
    test_state.user_preference = "I am an Arsenal fan and I love Saka"
    
    print(f"Test user preference: '{test_state.user_preference}'")
    print()
    
    # Run the agent
    updated_state = run(test_state)
    
    # Display results
    print()
    print("=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    print(f"Preferred entity: {updated_state.preferred_entity}")
    print(f"Match: {updated_state.match_context.home_team} vs {updated_state.match_context.away_team}")
    print(f"Events loaded: {len(updated_state.events)}")
    print(f"Highlight candidates: {len(updated_state.highlight_candidates)}")
    print()
    
    # Show first event
    if updated_state.events:
        print("First event:")
        first_event = updated_state.events[0]
        print(f"  Time: {first_event.time}")
        print(f"  Type: {first_event.event_type}")
        print(f"  Team: {first_event.team}")
        print(f"  Players: {', '.join(first_event.players)}")
        print(f"  Importance: {first_event.importance}")
        print(f"  Confidence: {first_event.confidence}")
