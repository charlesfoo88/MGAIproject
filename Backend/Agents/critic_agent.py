"""
Critic Agent - Stage 3: Evaluator

Validates LLM-generated captions to detect hallucinations by checking
if captions mention entities not present in the source event data.
Re-captions failed events up to MAX_RETRIES attempts.
"""

from typing import List, Optional, Tuple
from pathlib import Path

# Relative imports
try:
    from ..config import (
        LLM_PROVIDER,
        GROQ_API_KEY,
        GEMINI_API_KEY,
        GROQ_MODEL,
        GEMINI_MODEL,
        MAX_RETRIES,
        ALIGNMENT_THRESHOLD,
        HALLUCINATION_CHECK_PROMPT,
        CAPTION_PERSONALISED_PROMPT,
        CAPTION_NEUTRAL_PROMPT,
    )
    from ..State import SharedState
    from ..Schemas import HandoffEvent, ReelEvent, VerifiedOutput
    from ..Tools.embedding_tool import encode, cosine_similarity
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
        MAX_RETRIES,
        ALIGNMENT_THRESHOLD,
        HALLUCINATION_CHECK_PROMPT,
        CAPTION_PERSONALISED_PROMPT,
        CAPTION_NEUTRAL_PROMPT,
    )
    from State import SharedState
    from Schemas import HandoffEvent, ReelEvent, VerifiedOutput
    from Tools.embedding_tool import encode, cosine_similarity
    from Tools import lookup as rag_lookup


# Import LLM providers
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Import LangChain
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser


# ============================================================================
# Helper Functions
# ============================================================================

def find_handoff_event(segment_id: str, events: List[HandoffEvent]) -> Optional[HandoffEvent]:
    """
    Find the original HandoffEvent that corresponds to a ReelEvent.
    
    Args:
        segment_id: ReelEvent segment_id (same as clip_id)
        events: List of HandoffEvent objects from shared_state.events
        
    Returns:
        Matching HandoffEvent or None
    """
    for event in events:
        if event.clip_id == segment_id:
            return event
    return None


def extract_confirmed_entities(event: HandoffEvent, shared_state: SharedState) -> str:
    """
    Extract confirmed entities (teams, players, score, venue) from a HandoffEvent.
    
    Args:
        event: HandoffEvent object
        shared_state: SharedState with match context
        
    Returns:
        Formatted string of confirmed entities
    """
    entities = []
    has_specific_entities = False
    
    # Add team
    if event.team:
        entities.append(f"- Team: {event.team}")
        has_specific_entities = True
    
    # Add players
    if event.players:
        for player in event.players:
            entities.append(f"- Player: {player}")
            has_specific_entities = True
    
    # Add score after event
    if event.score_after_event:
        entities.append(f"- Score after event: {event.score_after_event}")
        has_specific_entities = True
    
    # Add match context information
    if shared_state.match_context:
        match_ctx = shared_state.match_context
        entities.append(f"- Home team: {match_ctx.home_team}")
        entities.append(f"- Away team: {match_ctx.away_team}")
        entities.append(f"- Venue: {match_ctx.venue}")
        has_specific_entities = True
        
        # Add venue knowledge base lookup
        if match_ctx.venue:
            entities.append(f"- Stadium nicknames and short forms of {match_ctx.venue} are also confirmed")

    # Add structured-first KB facts to support hallucination checks
    kb_context = build_event_rag_context(event, shared_state)
    if kb_context:
        for fact_block in kb_context.split("\n\n"):
            entities.append(f"- KB context: {fact_block}")
    
    # Always add common confirmed football terms
    entities.append("- Stadium aliases: Emirates, The Emirates, Etihad, The Etihad, Wembley, Anfield, Old Trafford are all confirmed venues")
    entities.append("- Fan terms: Gunners, Citizens, Blues, Reds, the faithful, supporters are confirmed fan terminology")
    entities.append("- Generic terms: standing ovation, incredible, stunning, brilliant, electric are confirmed descriptive terms")
    
    # Add note about acceptable generic terms
    entities.append("- Nicknames, aliases, generic football terms (attacker, goalkeeper, striker, spot, the cup, glory) and venue names are also confirmed.")
    
    # If no event-specific entities, add generic note
    if not has_specific_entities:
        entities.insert(0, "- No specific entities confirmed for this event")
    
    return "\n".join(entities)


def build_event_rag_context(event: HandoffEvent, shared_state: SharedState) -> str:
    """
    Build event-level RAG context using structured-first KB lookup.
    """
    rag_facts = []
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
            seen_entities.add(normalized)

    add_fact(shared_state.preferred_entity)
    add_fact(event.team)

    for player in event.players:
        add_fact(player)

    if shared_state.match_context:
        match_ctx = shared_state.match_context
        add_fact(match_ctx.home_team)
        add_fact(match_ctx.away_team)
        add_fact(match_ctx.venue)
        add_fact(match_ctx.competition)

    return "\n\n".join(rag_facts) if rag_facts else ""


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


def build_langchain_chain(template_path: Path, provider: str, temperature: float = 0.7, max_tokens: int = 150):
    """
    Build a LangChain chain: PromptTemplate | LLM | StrOutputParser
    
    Args:
        template_path: Path to prompt template file
        provider: "groq" or "gemini"
        temperature: LLM temperature (default 0.7)
        max_tokens: Maximum tokens to generate (default 150)
        
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
            temperature=temperature,
            max_tokens=max_tokens
        )
    else:
        llm = ChatGoogleGenerativeAI(
            google_api_key=GEMINI_API_KEY,
            model=GEMINI_MODEL,
            temperature=temperature,
            max_output_tokens=max_tokens
        )
    
    return prompt | llm | StrOutputParser()


def fill_hallucination_check_prompt(template: str, caption: str, confirmed_entities: str) -> str:
    """
    Fill hallucination check prompt template with caption and entities.
    
    Args:
        template: Template string
        caption: Caption text to validate
        confirmed_entities: Formatted string of confirmed entities
        
    Returns:
        Filled prompt string
    """
    return template.format(
        caption_text=caption,
        confirmed_entities=confirmed_entities
    )


def call_llm(prompt: str, provider: str) -> str:
    """
    Call LLM provider with prompt.
    
    Args:
        prompt: Filled prompt string
        provider: "groq" or "gemini"
        
    Returns:
        LLM response text
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
                temperature=0.3,  # Lower temperature for factual checking
                max_tokens=100,
            )
            result = response.choices[0].message.content.strip()
            return result
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
            result = response.text.strip()
            return result
        except Exception as e:
            print(f"✗ Gemini API error: {e}")
            return f"[ERROR: {str(e)}]"
    
    else:
        return f"[ERROR: Unknown provider: {provider}]"


def check_hallucination(
    reel_event: ReelEvent,
    handoff_event: HandoffEvent,
    shared_state: SharedState,
    chain
) -> Tuple[bool, str]:
    """
    Check if a caption contains hallucinated entities.
    
    Args:
        reel_event: ReelEvent with caption to check
        handoff_event: Original HandoffEvent with confirmed entities
        shared_state: SharedState with match context
        chain: LangChain chain for hallucination checking
        
    Returns:
        Tuple of (is_hallucinated, llm_response)
    """
    # Extract confirmed entities
    confirmed_entities = extract_confirmed_entities(handoff_event, shared_state)
    
    # Build variables dict
    variables = {
        'caption_text': reel_event.caption,
        'confirmed_entities': confirmed_entities
    }
    
    # Invoke LangChain chain
    llm_response = chain.invoke(variables)
    
    # Parse response - check if it's a genuine FAIL (not a self-corrected one)
    response_upper = llm_response.upper()
    is_hallucinated = (
        llm_response.startswith("FAIL") and 
        "PASS" not in response_upper.split("FAIL")[1] if "FAIL" in response_upper else False
    )
    
    return is_hallucinated, llm_response


def recaption_event(
    handoff_event: HandoffEvent,
    shared_state: SharedState,
    chain
) -> str:
    """
    Regenerate caption for an event.
    
    Args:
        handoff_event: Original HandoffEvent
        shared_state: SharedState with match context
        chain: LangChain chain for caption generation (personalized or neutral)
        
    Returns:
        New caption text
    """
    # Extract match context
    match_ctx = shared_state.match_context
    
    # Structured-first RAG context for recaption prompt
    rag_context = build_event_rag_context(handoff_event, shared_state)

    # Prepare variables for caption generation (same as fan_agent)
    variables = {
        'competition': match_ctx.competition if match_ctx else "Unknown",
        'home_team': match_ctx.home_team if match_ctx else "Unknown",
        'away_team': match_ctx.away_team if match_ctx else "Unknown",
        'final_score': match_ctx.final_score if match_ctx else "Unknown",
        'preferred_entity': shared_state.preferred_entity or "Unknown",
        'event_type': handoff_event.event_type,
        'minute': handoff_event.time,
        'team': handoff_event.team or "Unknown",
        'players': ", ".join(handoff_event.players) if handoff_event.players else "Unknown",
        'score_after_event': handoff_event.score_after_event,
        'emotion_tags': ", ".join(handoff_event.context.narrative.split()[:5]) if hasattr(handoff_event.context, 'narrative') else "Unknown",
        'narrative_context': handoff_event.context.narrative if hasattr(handoff_event.context, 'narrative') else "Unknown",
        'rag_context': rag_context or "No additional context available",
        'transcript_context': handoff_event.context.narrative if hasattr(handoff_event.context, 'narrative') else "No commentary available",
    }
    
    # Invoke LangChain chain
    new_caption = chain.invoke(variables)
    return new_caption.strip()


# ============================================================================
# Main Agent Function
# ============================================================================

def run(shared_state: SharedState) -> VerifiedOutput:
    """
    Critic Agent - Main execution function.
    
    Validates all captions in reel_a_events and reel_b_events for hallucinations.
    Re-captions failed events up to MAX_RETRIES.
    
    Args:
        shared_state: SharedState with reel events and captions
        
    Returns:
        VerifiedOutput with validated reels
    """
    print("\n" + "=" * 70)
    print("Stage 3: Critic Agent (Evaluator)")
    print("=" * 70)
    
    provider = LLM_PROVIDER
    print(f"Using LLM provider: {provider}")
    print(f"Max retries: {MAX_RETRIES}")
    print(f"Current retry count: {shared_state.retry_count}")
    
    # Build LangChain chain for hallucination checking
    print("\nBuilding hallucination check chain...")
    check_chain = build_langchain_chain(HALLUCINATION_CHECK_PROMPT, provider, temperature=0.3, max_tokens=100)
    print("✓ Chain built")
    
    # Build LangChain chains for recaptioning
    print("Building recaption chains...")
    recaption_chain_personalized = build_langchain_chain(CAPTION_PERSONALISED_PROMPT, provider, temperature=0.8, max_tokens=150)
    recaption_chain_neutral = build_langchain_chain(CAPTION_NEUTRAL_PROMPT, provider, temperature=0.8, max_tokens=150)
    print("✓ Chains built")
    
    # Track hallucinations
    hallucination_flagged = False
    unsupported_mentions = []
    
    # Verified reels (will be updated with recaptions if needed)
    verified_reel_a = list(shared_state.reel_a_events)
    verified_reel_b = list(shared_state.reel_b_events)
    
    # ========================================================================
    # Check Reel A (Personalized)
    # ========================================================================
    print(f"\n[Reel A] Checking {len(verified_reel_a)} captions...")
    print("-" * 70)
    
    for idx, reel_event in enumerate(verified_reel_a):
        print(f"  [{idx+1}/{len(verified_reel_a)}] {reel_event.event_type} @ segment {reel_event.segment_id}...", end=" ")
        
        # Find original HandoffEvent
        handoff_event = find_handoff_event(reel_event.segment_id, shared_state.events)
        
        if not handoff_event:
            print("⚠ Original event not found, skipping")
            continue
        
        # Check for hallucination
        is_hallucinated, llm_response = check_hallucination(
            reel_event,
            handoff_event,
            shared_state,
            check_chain
        )
        
        if is_hallucinated:
            print(f"✗ FAIL")
            print(f"      LLM: {llm_response}")
            hallucination_flagged = True
            
            # Extract unsupported mentions from response
            if "FAIL:" in llm_response:
                mentions = llm_response.split("FAIL:")[1].strip()
                unsupported_mentions.append(f"Reel A [{reel_event.segment_id}]: {mentions}")
            
            # Retry if within limit
            if shared_state.retry_count < MAX_RETRIES:
                print(f"      Retry {shared_state.retry_count + 1}/{MAX_RETRIES}: Re-captioning...")
                
                new_caption = recaption_event(
                    handoff_event,
                    shared_state,
                    recaption_chain_personalized
                )
                
                # Update the reel event with new caption
                verified_reel_a[idx] = ReelEvent(
                    segment_id=reel_event.segment_id,
                    clip_start_sec=reel_event.clip_start_sec,
                    clip_end_sec=reel_event.clip_end_sec,
                    caption=new_caption,
                    event_type=reel_event.event_type,
                    team=reel_event.team,
                )
                
                print(f"      ✓ New caption: {new_caption[:60]}...")
                shared_state.retry_count += 1
            else:
                print(f"      ⚠ Max retries reached, keeping original caption")
        else:
            print("✓ PASS")
    
    # ========================================================================
    # Check Reel B (Neutral)
    # ========================================================================
    print(f"\n[Reel B] Checking {len(verified_reel_b)} captions...")
    print("-" * 70)
    
    for idx, reel_event in enumerate(verified_reel_b):
        print(f"  [{idx+1}/{len(verified_reel_b)}] {reel_event.event_type} @ segment {reel_event.segment_id}...", end=" ")
        
        # Find original HandoffEvent
        handoff_event = find_handoff_event(reel_event.segment_id, shared_state.events)
        
        if not handoff_event:
            print("⚠ Original event not found, skipping")
            continue
        
        # Check for hallucination
        is_hallucinated, llm_response = check_hallucination(
            reel_event,
            handoff_event,
            shared_state,
            check_chain
        )
        
        if is_hallucinated:
            print(f"✗ FAIL")
            print(f"      LLM: {llm_response}")
            hallucination_flagged = True
            
            # Extract unsupported mentions from response
            if "FAIL:" in llm_response:
                mentions = llm_response.split("FAIL:")[1].strip()
                unsupported_mentions.append(f"Reel B [{reel_event.segment_id}]: {mentions}")
            
            # Retry if within limit
            if shared_state.retry_count < MAX_RETRIES:
                print(f"      Retry {shared_state.retry_count + 1}/{MAX_RETRIES}: Re-captioning...")
                
                new_caption = recaption_event(
                    handoff_event,
                    shared_state,
                    recaption_chain_neutral
                )
                
                # Update the reel event with new caption
                verified_reel_b[idx] = ReelEvent(
                    segment_id=reel_event.segment_id,
                    clip_start_sec=reel_event.clip_start_sec,
                    clip_end_sec=reel_event.clip_end_sec,
                    caption=new_caption,
                    event_type=reel_event.event_type,
                    team=reel_event.team,
                )
                
                print(f"      ✓ New caption: {new_caption[:60]}...")
                shared_state.retry_count += 1
            else:
                print(f"      ⚠ Max retries reached, keeping original caption")
        else:
            print("✓ PASS")
    
    # ========================================================================
    # Preference Alignment Scoring
    # ========================================================================
    print("\n" + "=" * 70)
    print("Preference Alignment Scoring")
    print("=" * 70)
    
    # Encode user preference once
    user_pref_embedding = encode(shared_state.user_preference)
    print(f"User preference: {shared_state.user_preference}")
    print(f"Encoding user preference...")
    
    # Score Reel A captions (personalized)
    reel_a_scores = []
    
    print("\n[Reel A - Personalized] Computing alignment scores...")
    for idx, reel_event in enumerate(verified_reel_a):
        caption_embedding = encode(reel_event.caption)
        score = cosine_similarity(caption_embedding, user_pref_embedding)
        reel_a_scores.append(score)
        print(f"  [{idx+1}] {reel_event.caption[:40]}... → {score:.3f}")
    
    # Score Reel B captions (neutral)
    reel_b_scores = []
    
    print("\n[Reel B - Neutral] Computing alignment scores...")
    for idx, reel_event in enumerate(verified_reel_b):
        caption_embedding = encode(reel_event.caption)
        score = cosine_similarity(caption_embedding, user_pref_embedding)
        reel_b_scores.append(score)
        print(f"  [{idx+1}] {reel_event.caption[:40]}... → {score:.3f}")
    
    # Compute average alignment scores
    reel_a_alignment_score = sum(reel_a_scores) / len(reel_a_scores) if reel_a_scores else 0.0
    reel_b_alignment_score = sum(reel_b_scores) / len(reel_b_scores) if reel_b_scores else 0.0
    
    # Combine all scores for compatibility
    preference_alignment_scores = reel_a_scores + reel_b_scores
    
    # Flag if Reel A alignment is too low (only check personalized reel)
    alignment_flagged = reel_a_alignment_score < ALIGNMENT_THRESHOLD
    
    print("\n" + "-" * 70)
    print(f"Reel A (Personalized) alignment: {reel_a_alignment_score:.3f}")
    print(f"  Quality: {'⚠ LOW' if alignment_flagged else '✓ GOOD'} (threshold: {ALIGNMENT_THRESHOLD})")
    print(f"Reel B (Neutral) alignment: {reel_b_alignment_score:.3f}")
    print(f"  Note: Neutral captions are not expected to align with user preference")
    print("=" * 70)
    
    # ========================================================================
    # Build VerifiedOutput
    # ========================================================================
    print("\n" + "=" * 70)
    print("Validation Summary:")
    print(f"  Hallucinations detected: {'Yes' if hallucination_flagged else 'No'}")
    print(f"  Reel A alignment: {'Low' if alignment_flagged else 'Good'} ({reel_a_alignment_score:.3f})")
    print(f"  Reel B alignment: {reel_b_alignment_score:.3f} (neutral, no threshold)")
    print(f"  Total retries used: {shared_state.retry_count}/{MAX_RETRIES}")
    print(f"  Unsupported mentions: {len(unsupported_mentions)}")
    
    if unsupported_mentions:
        print("\nUnsupported mentions found:")
        for mention in unsupported_mentions:
            print(f"  - {mention}")
    
    print("=" * 70)
    
    verified_output = VerifiedOutput(
        hallucination_flagged=hallucination_flagged,
        retry_count=shared_state.retry_count,
        verified_reel_a=verified_reel_a,
        verified_reel_b=verified_reel_b,
        unsupported_mentions=unsupported_mentions,
        preference_alignment_scores=preference_alignment_scores,
        reel_a_alignment_score=reel_a_alignment_score,
        reel_b_alignment_score=reel_b_alignment_score,
    )
    
    return verified_output


# ============================================================================
# Test Harness
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Critic Agent - Standalone Test")
    print("=" * 70)
    print("\nThis test requires:")
    print("1. Run sports_analyst_agent first to populate shared_state.events")
    print("2. Run fan_agent to generate reel_a_events and reel_b_events")
    print("3. Then run this critic_agent to validate captions")
    print("\nUse tests/test_pipeline.py for full pipeline test.")
    print("=" * 70)
