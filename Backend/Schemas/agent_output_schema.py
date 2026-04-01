from pydantic import BaseModel
from typing import List, Optional


class ReelEvent(BaseModel):
    segment_id: str
    clip_start_sec: float
    clip_end_sec: float
    caption: str
    event_type: str
    team: Optional[str] = None


class AgentOutput(BaseModel):
    """Model for Fan Agent output"""
    reel_a_events: List[ReelEvent]
    reel_b_events: List[ReelEvent]
