from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from .agent_output_schema import ReelEvent, EvidenceSource


class DisagreementRecord(BaseModel):
    """Record of disagreement dialogue between Critic and Sports Analyst"""
    segment_id: str
    event_type: str
    importance_score: float
    round_1_challenge: str
    round_1_defence: str
    round_2_challenge: str
    round_2_defence: str
    outcome: str  # "confirmed" or "overridden"
    reason: str   # final reason for outcome


class VerifiedReelEvent(BaseModel):
    """Verified reel event with evidence passthrough"""
    segment_id: str
    clip_start_sec: float
    clip_end_sec: float
    caption: str
    event_type: str
    team: Optional[str] = None
    evidence: Optional[EvidenceSource] = None
    original_caption: Optional[str] = None  # caption before retry, None if not regenerated
    was_regenerated: bool = False            # True only if this specific clip was retried


class VerifiedOutput(BaseModel):
    """Model for Critic Agent output"""
    hallucination_flagged: bool
    retry_count: int
    verified_reel_a: List[VerifiedReelEvent]
    verified_reel_b: List[VerifiedReelEvent]
    unsupported_mentions: List[str] = []
    preference_alignment_scores: List[float] = []
    reel_a_alignment_score: float = 0.0
    reel_b_alignment_score: float = 0.0
    evidence_summary: Optional[Dict[str, Any]] = None
    disagreement_log: List[DisagreementRecord] = []
    # Summary of evidence sources across all captions
