from pydantic import BaseModel
from typing import List, Optional, Any
from .event_schema import HandoffEvent, ScoreProgression, EntityRegistry


class AgentInput(BaseModel):
    """Model for Sports Analyst Agent output to Fan Agent"""
    match_id: str
    home_team: str
    away_team: str
    competition: str
    venue: str
    preferred_entity: str
    events: List[HandoffEvent]
    score_progression: List[ScoreProgression]
    entity_registry: List[EntityRegistry]
    transcript_context: str
    rag_context: Optional[str] = None
