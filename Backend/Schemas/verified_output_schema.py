from pydantic import BaseModel
from typing import List
from .agent_output_schema import ReelEvent


class VerifiedOutput(BaseModel):
    """Model for Critic Agent output"""
    hallucination_flagged: bool
    retry_count: int
    verified_reel_a: List[ReelEvent]
    verified_reel_b: List[ReelEvent]
    unsupported_mentions: List[str] = []
    preference_alignment_scores: List[float] = []
    reel_a_alignment_score: float = 0.0
    reel_b_alignment_score: float = 0.0
