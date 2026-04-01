from typing import List, Dict, Optional
from pathlib import Path

# Relative imports
try:
    from ..Schemas import (
        HandoffEvent,
        HighlightCandidate,
        ReelEvent,
        MatchContext,
        EntityRegistry,
        ScoreProgression,
    )
except ImportError:
    # Direct execution fallback
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from Schemas import (
        HandoffEvent,
        HighlightCandidate,
        ReelEvent,
        MatchContext,
        EntityRegistry,
        ScoreProgression,
    )


class SharedState:
    """Simple shared state class for persisting data across all three agents in the MGAI pipeline"""
    
    def __init__(self):
        # D15 & D17 pipeline data
        self.events: List[HandoffEvent] = []
        self.highlight_candidates: List[HighlightCandidate] = []
        
        # User preferences
        self.user_preference: Optional[str] = None
        self.preferred_entity: Optional[str] = None
        self.query_transformed: Optional[dict] = None  # LLM-extracted: {preferred_team, preferred_players, search_terms}
        
        # Fan Agent outputs
        self.reel_a_events: List[ReelEvent] = []
        self.reel_b_events: List[ReelEvent] = []
        self.captions: Dict[str, str] = {}  # segment_id -> caption string
        
        # Retry tracking
        self.retry_count: int = 0
        
        # Match metadata
        self.match_context: Optional[MatchContext] = None
        self.entity_registry: List[EntityRegistry] = []
        self.score_progression: List[ScoreProgression] = []
        self.match_recap: Optional[str] = None
    
    def reset(self):
        """Reset retry count to 0"""
        self.retry_count = 0
