"""Pydantic schemas for MGAI Backend"""

from .event_schema import (
    HighlightCandidate,
    DLHandoff,
    MatchContext,
    EntityRegistry,
    HandoffEvent,
    ScoreProgression,
    TimeRange,
    ScoreContext,
    ModalityScores,
    FeatureVector,
    TopLabel,
    DynamicAdjustments,
    EventContext,
)
from .agent_input_schema import AgentInput
from .agent_output_schema import AgentOutput, ReelEvent
from .verified_output_schema import VerifiedOutput

__all__ = [
    # Event schemas (D15 & D17)
    "HighlightCandidate",
    "DLHandoff",
    "MatchContext",
    "EntityRegistry",
    "HandoffEvent",
    "ScoreProgression",
    "TimeRange",
    "ScoreContext",
    "ModalityScores",
    "FeatureVector",
    "TopLabel",
    "DynamicAdjustments",
    "EventContext",
    # Agent schemas
    "AgentInput",
    "AgentOutput",
    "ReelEvent",
    "VerifiedOutput",
]
