"""
Fan Agent - Stage 2: Executor

Selects highlight clips based on user preferences and generates personalized
and neutral captions using LLM providers (Groq or Gemini).
"""

from typing import List, Optional
from pathlib import Path

# Relative imports
try:
    from ..config import (
        LLM_PROVIDER,
        GROQ_API_KEY,
        GEMINI_API_KEY,
        GROQ_MODEL,
        GEMINI_MODEL,
        IMPORTANCE_THRESHOLD,
        MAX_HIGHLIGHTS,
        EVENT_IMPORTANCE,
        CAPTION_PERSONALISED_PROMPT,
        CAPTION_NEUTRAL_PROMPT,
    )
    from ..State import SharedState
    from ..Schemas import HandoffEvent, ReelEvent
    from ..Schemas.agent_output_schema import EvidenceSource
    from ..Tools import lookup as rag_lookup
except ImportError:
    # Direct execution fallback
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from config import (
        LLM_PROVIDER,
        GROQ_API_KEY,
        GEMINI_API_KEY,
        GROQ_MODEL,
        GEMINI_MODEL,
        IMPORTANCE_THRESHOLD,
        MAX_HIGHLIGHTS,
        EVENT_IMPORTANCE,
        CAPTION_PERSONALISED_PROMPT,
        CAPTION_NEUTRAL_PROMPT,
    )
    from State import SharedState
    from Schemas import HandoffEvent, ReelEvent
    from Schemas.agent_output_schema import EvidenceSource
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

# Import LangChain
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser


def select_clips_reel_a(
    events: List[HandoffEvent],
    preferred_entity: Optional[str],
    importance_threshold: float,
    max_highlights: int
) -> List[HandoffEvent]:
    """
    Select clips for Reel A (personalized).
    
    Selection strategy:
    1. Always include all goals (regardless of which team scored)
    2. Fill remaining slots with highest importance non-goal events (all teams)
    3. Never include substitutions unless fewer than 3 other events available
    4. Captions will provide the fan perspective, not the event selection
    5. Both teams see the same events, but with different narrative framing
    
    Args:
        events: List of HandoffEvent objects
        preferred_entity: User's preferred team/player
        importance_threshold: Minimum importance score
        max_highlights: Maximum number of clips to select
        
    Returns:
        List of selected HandoffEvent objects for Reel A
    """
    if not preferred_entity:
        print("⚠ No preferred entity specified for Reel A - using neutral selection")
        return select_clips_reel_b(events, importance_threshold, max_highlights)
    
    # Filter events by threshold and valid timestamps
    valid_events = [
        e for e in events
        if e.importance >= importance_threshold
        and e.clip_start_sec is not None
        and e.clip_end_sec is not None
    ]
    
    # Separate ALL goals from non-goals (goals shown regardless of team)
    all_goals = [e for e in valid_events if e.event_type in ['goal', 'penalty_goal']]
    all_non_goals = [e for e in valid_events if e.event_type not in ['goal', 'penalty_goal']]
    
    # Sort all goals by importance
    all_goals_sorted = sorted(all_goals, key=lambda e: e.importance, reverse=True)
    
    # Start with ALL goals (up to max_highlights)
    selected = all_goals_sorted[:max_highlights]
    
    # Fill remaining slots with ALL non-goal events (captions will provide perspective)
    slots_remaining = max_highlights - len(selected)
    if slots_remaining > 0:
        # Include ALL non-goal events, let captions provide the fan perspective
        # Exclude substitutions unless few events
        non_subs = [e for e in all_non_goals if e.event_type != 'substitution']
        subs = [e for e in all_non_goals if e.event_type == 'substitution']
        
        non_subs_sorted = sorted(non_subs, key=lambda e: e.importance, reverse=True)
        selected.extend(non_subs_sorted[:slots_remaining])
        
        # Add substitutions only if still have slots and <3 other events
        slots_remaining = max_highlights - len(selected)
        if slots_remaining > 0 and len(non_subs) < 3:
            subs_sorted = sorted(subs, key=lambda e: e.importance, reverse=True)
            selected.extend(subs_sorted[:slots_remaining])
    
    print(f"Reel A: {len(events)} events -> {len(valid_events)} valid ({len(all_goals)} goals) -> {len(selected)} selected")
    
    return selected


def select_clips_reel_b(
    events: List[HandoffEvent],
    importance_threshold: float,
    max_highlights: int
) -> List[HandoffEvent]:
    """
    Select clips for Reel B (neutral).
    
    Selection strategy:
    1. Always include all goals first
    2. Fill remaining slots with next highest importance events
    3. Never include substitutions unless fewer than 3 other events available
    4. Always select exactly max_highlights clips or all available if fewer
    
    Args:
        events: List of HandoffEvent objects
        importance_threshold: Minimum importance score
        max_highlights: Maximum number of clips to select
        
    Returns:
        List of selected HandoffEvent objects for Reel B
    """
    # Filter by importance threshold and valid timestamps
    filtered = [
        event for event in events 
        if event.importance >= importance_threshold
        and event.clip_start_sec is not None
        and event.clip_end_sec is not None
    ]
    
    # Separate goals from other events
    goals = [e for e in filtered if e.event_type in ['goal', 'penalty_goal']]
    non_goals = [e for e in filtered if e.event_type not in ['goal', 'penalty_goal']]
    
    # Sort goals by importance descending
    goals_sorted = sorted(goals, key=lambda e: e.importance, reverse=True)
    
    # Start with all goals
    selected = goals_sorted[:max_highlights]
    
    # Fill remaining slots with non-goal events
    slots_remaining = max_highlights - len(selected)
    if slots_remaining > 0:
        # Filter out substitutions unless we have fewer than 3 non-substitution events
        non_subs = [e for e in non_goals if e.event_type != 'substitution']
        subs = [e for e in non_goals if e.event_type == 'substitution']
        
        # Sort by importance
        non_subs_sorted = sorted(non_subs, key=lambda e: e.importance, reverse=True)
        
        # Add non-substitutions first
        selected.extend(non_subs_sorted[:slots_remaining])
        
        # Only add substitutions if we still have slots and fewer than 3 other events
        slots_remaining = max_highlights - len(selected)
        if slots_remaining > 0 and len(non_subs) < 3:
            subs_sorted = sorted(subs, key=lambda e: e.importance, reverse=True)
            selected.extend(subs_sorted[:slots_remaining])
    
    print(f"Reel B: {len(events)} events -> {len(filtered)} filtered ({len(goals)} goals) -> {len(selected)} selected")
    
    return selected


def load_prompt_template(template_path: Path) -> str:
    """
    Load prompt template from file.
    
    Args:
        template_path: Path to prompt template file
        
    Returns:
        Template string with {variable} placeholders
    """
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    return template


def build_langchain_chain(template_path: Path, provider: str):
    """
    Build a LangChain chain: PromptTemplate | LLM | StrOutputParser
    
    Args:
        template_path: Path to prompt template file
        provider: "groq" or "gemini"
        
    Returns:
        LangChain chain (PromptTemplate | LLM | StrOutputParser)
    """
    with open(template_path, 'r', encoding='utf-8') as f:
        template_text = f.read()
    
    prompt = PromptTemplate.from_template(template_text)
    
    if provider == "groq":
        llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model=GROQ_MODEL,
            temperature=0.7,
            max_tokens=300
        )
    else:
        llm = ChatGoogleGenerativeAI(
            google_api_key=GEMINI_API_KEY,
            model=GEMINI_MODEL,
            temperature=0.7,
            max_output_tokens=300
        )
    
    return prompt | llm | StrOutputParser()


def build_event_rag_context(event: HandoffEvent, shared_state: SharedState) -> tuple[str, list[str]]:
    """
    Build event-level RAG context using structured-first KB lookup.
    
    Returns:
        Tuple of (context_string, entities_found)
        - context_string: Formatted RAG facts for prompt
        - entities_found: List of entity names that had KB facts
    """
    rag_facts = []
    rag_entities_found = []
    seen_entities = set()

    def add_fact(entity: Optional[str]):
        if not entity:
            return

        normalized = entity.strip().lower()
        if not normalized or normalized in seen_entities:
            return

        fact = rag_lookup(entity)
        if fact:
            rag_facts.append(f"[{entity}] {fact}")
            rag_entities_found.append(entity)
            seen_entities.add(normalized)

    add_fact(shared_state.preferred_entity)
    add_fact(event.team)

    for player in event.players:
        add_fact(player)

    if shared_state.match_context and shared_state.match_context.venue:
        add_fact(shared_state.match_context.venue)

    context_str = "\n\n".join(rag_facts) if rag_facts else ""
    return context_str, rag_entities_found


def fill_prompt_template(
    template: str,
    event: HandoffEvent,
    shared_state: SharedState,
    rag_context: Optional[str] = None,
    transcript_context: Optional[str] = None
) -> str:
    """
    Fill prompt template with event data.
    
    Args:
        template: Template string with {variable} placeholders
        event: HandoffEvent object
        shared_state: SharedState with match context
        rag_context: Optional RAG context for this event
        transcript_context: Optional transcript context for this event
        
    Returns:
        Filled prompt string
    """
    # Extract match context
    match_ctx= shared_state.match_context
    
    # For goals, use explicit scorer/assist if available to avoid LLM confusion
    players_str = ", ".join(event.players) if event.players else "Unknown"
    if hasattr(event, 'scorer') and event.scorer:
        players_str = f"Scorer: {event.scorer}"
        if hasattr(event, 'assist') and event.assist:
            players_str += f", Assist: {event.assist}"
    
    # Prepare variables
    variables = {
        'competition': match_ctx.competition if match_ctx else "Unknown",
        'home_team': match_ctx.home_team if match_ctx else "Unknown",
        'away_team': match_ctx.away_team if match_ctx else "Unknown",
        'final_score': match_ctx.final_score if match_ctx else "Unknown",
        'preferred_entity': shared_state.preferred_entity or "Unknown",
        'event_type': event.event_type,
        'minute': event.time,
        'team': event.team or "Unknown",
        'players': players_str,
        'score_after_event': event.score_after_event,
        'emotion_tags': ", ".join(event.context.narrative.split()[:5]) if hasattr(event.context, 'narrative') else "Unknown",
        'narrative_context': event.context.narrative if hasattr(event.context, 'narrative') else "Unknown",
        'rag_context': rag_context or "No additional context available",
        'transcript_context': transcript_context or "No commentary available",
    }
    
    # Fill template
    try:
        filled = template.format(**variables)
    except KeyError as e:
        print(f"⚠ Missing variable in template: {e}")
        filled = template
    
    return filled


def call_llm(prompt: str, provider: str) -> str:
    """
    Call LLM provider with prompt.
    
    Args:
        prompt: Filled prompt string
        provider: "groq" or "gemini"
        
    Returns:
        Generated caption text
    """
    if provider == "groq":
        if not GROQ_AVAILABLE:
            return "[ERROR: Groq not available]"
        if not GROQ_API_KEY:
            return "[ERROR: GROQ_API_KEY not set]"
        
        try:
            client = Groq(api_key=GROQ_API_KEY)
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=150,
            )
            caption = response.choices[0].message.content.strip()
            return caption
        except Exception as e:
            print(f"✗ Groq API error: {e}")
            return f"[ERROR: {str(e)}]"
    
    elif provider == "gemini":
        if not GEMINI_AVAILABLE:
            return "[ERROR: Gemini not available]"
        if not GEMINI_API_KEY:
            return "[ERROR: GEMINI_API_KEY not set]"
        
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel(GEMINI_MODEL)
            response = model.generate_content(prompt)
            caption = response.text.strip()
            return caption
        except Exception as e:
            print(f"✗ Gemini API error: {e}")
            return f"[ERROR: {str(e)}]"
    
    else:
        return f"[ERROR: Unknown provider '{provider}']"


def generate_captions(
    events: List[HandoffEvent],
    template_path: Path,
    shared_state: SharedState,
    provider: str,
    reel_name: str
) -> List[ReelEvent]:
    """
    Generate captions for all events using LLM via LangChain.
    
    Args:
        events: List of HandoffEvent objects
        template_path: Path to prompt template
        shared_state: SharedState with match context
        provider: "groq" or "gemini"
        reel_name: "Reel A" or "Reel B" for logging
        
    Returns:
        List of ReelEvent objects with captions
    """
    print(f"[{reel_name}] Generating {len(events)} captions using {provider}...")
    
    # Build LangChain chain once for all captions
    chain = build_langchain_chain(template_path, provider)
    
    reel_events = []
    
    for idx, event in enumerate(events, 1):
        print(f"  [{idx}/{len(events)}] {event.event_type} @ {event.time}...", end=" ")
        
        # Build variables dict for this event
        match_ctx = shared_state.match_context
        rag_context, rag_entities_found = build_event_rag_context(event, shared_state)
        transcript_context = event.context.narrative if hasattr(event.context, 'narrative') else None
        
        # For goals, use explicit scorer/assist if available
        players_str = ", ".join(event.players) if event.players else "Unknown"
        if hasattr(event, 'scorer') and event.scorer:
            players_str = f"Scorer: {event.scorer}"
            if hasattr(event, 'assist') and event.assist:
                players_str += f", Assist: {event.assist}"
        
        variables = {
            'competition': match_ctx.competition if match_ctx else "Unknown",
            'home_team': match_ctx.home_team if match_ctx else "Unknown",
            'away_team': match_ctx.away_team if match_ctx else "Unknown",
            'final_score': match_ctx.final_score if match_ctx else "Unknown",
            'preferred_entity': shared_state.preferred_entity or "Unknown",
            'event_type': event.event_type,
            'minute': event.time,
            'team': event.team or "Unknown",
            'players': players_str,
            'score_after_event': event.score_after_event,
            'emotion_tags': ", ".join(event.context.narrative.split()[:5]) if hasattr(event.context, 'narrative') else "Unknown",
            'narrative_context': event.context.narrative if hasattr(event.context, 'narrative') else "Unknown",
            'rag_context': rag_context or "No additional context available",
            'transcript_context': transcript_context or "No commentary available",
        }
        
        # Build prompt_used by manually filling template
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_text = f.read()
            prompt_used = template_text.format(**variables)
        except Exception as e:
            print(f"⚠ Could not build prompt_used: {e}")
            prompt_used = ""
        
        # Invoke LangChain chain with variables - retry once if caption incomplete
        max_retries = 2
        caption = None
        
        for retry in range(max_retries):
            temp_caption = chain.invoke(variables)
            word_count = len(temp_caption.split())
            
            # Validate: must be at least 8 words and end with punctuation (complete sentence)
            is_complete = word_count >= 8
            ends_properly = temp_caption.strip() and temp_caption.strip()[-1] in '.!?'
            
            if is_complete and ends_properly:
                caption = temp_caption
                if retry > 0:
                    print(f"[OK-retry:{retry}] ", end="")
                break
            else:
                if retry < max_retries - 1:
                    print(f"[!{word_count}w] ", end="")
                    import time
                    time.sleep(0.5)  # Brief pause between retries
                else:
                    # Use it anyway after max retries
                    caption = temp_caption
                    print(f"[!INCOMPLETE:{word_count}w] ", end="")
        
        # Build evidence record for this caption
        # Split rag_context into individual fact strings
        rag_fact_texts = rag_context.split("\n\n") if rag_context else []
        
        evidence = EvidenceSource(
            d15_fields={
                "importance_score": event.importance,
                "confidence": event.confidence,
                "predicted_event_type": event.event_type,
            },
            d17_fields={
                "narrative": event.context.narrative if event.context else None,
                "score_after_event": event.score_after_event,
                "players": event.players,
                "event_type": event.event_type,
            },
            rag_facts=rag_entities_found,
            rag_fact_texts=rag_fact_texts,
            transcript_chunks=[event.context.narrative] if event.context else [],
            prompt_used=prompt_used
        )
        
        # Create ReelEvent
        reel_event = ReelEvent(
            segment_id=event.clip_id,
            clip_start_sec=event.clip_start_sec,
            clip_end_sec=event.clip_end_sec,
            caption=caption,
            event_type=event.event_type,
            team=event.team,
            evidence=evidence,
        )
        
        reel_events.append(reel_event)
        
        print(f"✓ ({len(caption)} chars)")
    
    print(f"✓ [{reel_name}] Generated {len(reel_events)} captions")
    
    return reel_events


def generate_match_recap(shared_state: SharedState, provider: str) -> str:
    """
    Generate a neutral 3-4 sentence match recap covering the full match narrative.
    
    Args:
        shared_state: SharedState with match_context and score_progression
        provider: "groq" or "gemini"
        
    Returns:
        Match recap string
    """
    match_ctx = shared_state.match_context
    score_prog = shared_state.score_progression
    
    # Build prompt
    prompt = f"""You are a sports journalist writing a neutral match recap.

Match Information:
- Competition: {match_ctx.competition}
- Venue: {match_ctx.venue}
- Teams: {match_ctx.home_team} vs {match_ctx.away_team}
- Final Score: {match_ctx.final_score}

Score Progression:
"""
    
    for sp in score_prog:
        prompt += f"- {sp.time}: {sp.scorer} ({sp.team}) - Score: {sp.score}\n"
    
    prompt += """\nTask: Write a neutral 3-4 sentence match recap covering:
- Opening goal and early match flow
- Key turning points and momentum shifts
- Final result and overall match narrative

Keep it factual, engaging, and suitable for a neutral viewer.

Match recap:"""
    
    # Build LangChain chain for match recap
    if provider == "groq":
        llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model=GROQ_MODEL,
            temperature=0.7,
            max_tokens=250
        )
    else:
        llm = ChatGoogleGenerativeAI(
            google_api_key=GEMINI_API_KEY,
            model=GEMINI_MODEL,
            temperature=0.7,
            max_output_tokens=250
        )
    
    chain = llm | StrOutputParser()
    recap = chain.invoke(prompt)
    
    return recap.strip()


def run(shared_state: SharedState) -> SharedState:
    """
    Fan Agent - Main execution function.
    
    Stage 2: Select highlight clips and generate personalized/neutral captions.
    
    Args:
        shared_state: SharedState object with events from sports_analyst_agent
        
    Returns:
        Updated SharedState with reel_a_events and reel_b_events
    """
    print("=" * 70)
    print("FAN AGENT - Stage 2: Executor")
    print("=" * 70)
    print()
    
    # Validate inputs
    if not shared_state.events:
        print("✗ No events in shared_state. Run sports_analyst_agent first.")
        return shared_state
    
    print(f"Input: {len(shared_state.events)} events from sports_analyst_agent")
    print(f"Preferred entity: {shared_state.preferred_entity}")
    print(f"LLM provider: {LLM_PROVIDER}")
    print(f"Importance threshold: {IMPORTANCE_THRESHOLD}")
    print(f"Max highlights per reel: {MAX_HIGHLIGHTS}")
    print()
    
    # Step 1: Select clips for Reel A (personalized)
    print("[Step 1] Selecting clips for Reel A (personalized)...")
    reel_a_events_raw = select_clips_reel_a(
        shared_state.events,
        shared_state.preferred_entity,
        IMPORTANCE_THRESHOLD,
        MAX_HIGHLIGHTS
    )
    print()
    
    # Step 2: Select clips for Reel B (neutral)
    print("[Step 2] Selecting clips for Reel B (neutral)...")
    reel_b_events_raw = select_clips_reel_b(
        shared_state.events,
        IMPORTANCE_THRESHOLD,
        MAX_HIGHLIGHTS
    )
    print()
    
    # Step 3: Generate captions for Reel A
    print("[Step 3] Generating captions for Reel A...")
    if reel_a_events_raw:
        reel_a_events = generate_captions(
            reel_a_events_raw,
            CAPTION_PERSONALISED_PROMPT,
            shared_state,
            LLM_PROVIDER,
            "Reel A"
        )
    else:
        reel_a_events = []
        print("⚠ No events selected for Reel A")
    print()
    
    # Step 4: Generate captions for Reel B
    print("[Step 4] Generating captions for Reel B...")
    if reel_b_events_raw:
        reel_b_events = generate_captions(
            reel_b_events_raw,
            CAPTION_NEUTRAL_PROMPT,
            shared_state,
            LLM_PROVIDER,
            "Reel B"
        )
    else:
        reel_b_events = []
        print("⚠ No events selected for Reel B")
    print()
    
    # Step 5: Update SharedState
    print("[Step 5] Updating shared state...")
    shared_state.reel_a_events = reel_a_events
    shared_state.reel_b_events = reel_b_events
    
    # Build captions dict for video stitching
    for event in reel_a_events:
        shared_state.captions[event.segment_id] = event.caption
    for event in reel_b_events:
        shared_state.captions[event.segment_id] = event.caption
    
    print(f"✓ Reel A: {len(reel_a_events)} events with captions")
    print(f"✓ Reel B: {len(reel_b_events)} events with captions")
    print(f"✓ Total captions stored: {len(shared_state.captions)}")
    print()
    
    # Step 6: Generate match recap
    print("[Step 6] Generating neutral match recap...")
    match_recap = generate_match_recap(shared_state, LLM_PROVIDER)
    shared_state.match_recap = match_recap
    print(f"✓ Match recap generated ({len(match_recap)} chars)")
    print()
    
    print("=" * 70)
    print("✓ FAN AGENT COMPLETE")
    print("=" * 70)
    print()
    
    return shared_state


# Test harness
if __name__ == "__main__":
    print("Testing Fan Agent")
    print()
    
    # Import sports_analyst_agent to populate shared state
    try:
        from . import sports_analyst_agent
    except ImportError:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import sports_analyst_agent
    
    # Create test shared state with sports analyst output
    test_state = SharedState()
    test_state.user_preference = "I am an Arsenal fan and I love Saka"
    
    print("=" * 70)
    print("RUNNING SPORTS ANALYST AGENT FIRST")
    print("=" * 70)
    print()
    
    # Run sports analyst agent to populate events
    test_state = sports_analyst_agent.run(test_state)
    
    print()
    print("=" * 70)
    print("NOW RUNNING FAN AGENT")
    print("=" * 70)
    print()
    
    # Run fan agent
    updated_state = run(test_state)
    
    # Display results
    print()
    print("=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    print(f"Reel A events: {len(updated_state.reel_a_events)}")
    print(f"Reel B events: {len(updated_state.reel_b_events)}")
    print()
    
    # Show sample from Reel A
    if updated_state.reel_a_events:
        print("Sample from Reel A:")
        sample = updated_state.reel_a_events[0]
        print(f"  Segment: {sample.segment_id}")
        print(f"  Type: {sample.event_type}")
        print(f"  Team: {sample.team}")
        print(f"  Clip: {sample.clip_start_sec}s - {sample.clip_end_sec}s")
        print(f"  Caption: {sample.caption}")
        print()
    
    # Show sample from Reel B
    if updated_state.reel_b_events:
        print("Sample from Reel B:")
        sample = updated_state.reel_b_events[0]
        print(f"  Segment: {sample.segment_id}")
        print(f"  Type: {sample.event_type}")
        print(f"  Team: {sample.team}")
        print(f"  Clip: {sample.clip_start_sec}s - {sample.clip_end_sec}s")
        print(f"  Caption: {sample.caption}")
