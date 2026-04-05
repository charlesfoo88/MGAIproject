from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class EvidenceSource(BaseModel):
    """Tracks which sources contributed to a caption"""
    d15_fields: Dict[str, Any] = {}
    # D15 fields used: importance_score, emotion_tags, predicted_event_type
    d17_fields: Dict[str, Any] = {}
    # D17 fields used: narrative, score_after_event, players, context
    rag_facts: List[str] = []
    # List of entity names that had KB facts retrieved
    transcript_chunks: List[str] = []
    # Narrative chunks used from D4 audio summaries


class ReelEvent(BaseModel):
    segment_id: str
    clip_start_sec: float
    clip_end_sec: float
    caption: str
    event_type: str
    team: Optional[str] = None
    evidence: Optional[EvidenceSource] = None


class AgentOutput(BaseModel):
    """Model for Fan Agent output"""
    reel_a_events: List[ReelEvent]
    reel_b_events: List[ReelEvent]
