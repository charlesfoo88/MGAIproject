from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# D15 HighlightCandidate Schema
class TimeRange(BaseModel):
    start: float
    end: float


class ScoreContext(BaseModel):
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    score_change_detected: bool


class ModalityScores(BaseModel):
    audio: float
    visual: float
    context: float


class FeatureVector(BaseModel):
    audio_peak: float
    audio_density: float
    audio_excitement: float
    audio_whistle: float
    audio_applause: float
    audio_crowd: float
    audio_commentary: float
    audio_score_update: float
    audio_celebration: float
    audio_foul_or_penalty: float
    audio_stoppage_review: float
    audio_substitution: float
    audio_injury_pause: float
    audio_high_tension: float
    visual_motion: float
    visual_replay: float
    visual_ocr: float
    visual_face: float
    visual_face_count: float
    visual_positive_emotion: float
    visual_negative_emotion: float
    visual_surprise: float
    context_scoreboard_visible: float
    context_crowd_reaction: float
    context_celebration: float
    context_disappointment: float
    context_stoppage_review: float
    context_bench_reaction: float
    context_highlight_package: float
    context_substitution: float
    context_injury: float
    context_high_tension: float


class TopLabel(BaseModel):
    label: str
    score: float


class DynamicAdjustments(BaseModel):
    score_change: Optional[float] = None
    celebration: Optional[float] = None
    crowd_peak: Optional[float] = None


class HighlightCandidate(BaseModel):
    """Model for D15 highlight_candidates_mock.json"""
    segment_id: str
    time_range: TimeRange
    predicted_event_type: str
    confidence: float
    importance_score: float
    importance_rank: int
    team: Optional[str] = None
    players: List[str]
    score_after_event: str
    score_context: ScoreContext
    match_phase: str
    match_time_display: str
    ocr_text: List[str]
    modality_scores: ModalityScores
    feature_vector: FeatureVector
    top_labels: List[TopLabel]
    context_tags: List[str]
    emotion_tags: List[str]
    domain_inference: str
    domain_confidence: float
    about_summary: str
    judgment_criteria: List[str]
    context_summary: str
    prompt_template: str
    analysis_prompt: str
    dynamic_adjustments: DynamicAdjustments
    supporting_audio_event_ids: List[str]
    supporting_video_event_ids: List[str]
    rationale: List[str]
    heuristic_importance_score: float
    learned_importance_score: Optional[float] = None
    ranking_model: str
    importance_reasons: List[Any]


# D17 DLHandoff Schema
class MatchContext(BaseModel):
    match_id: str
    video_id: str
    competition: str
    season: str
    date: str
    venue: str
    home_team: str
    away_team: str
    final_score: str


class EntityRegistry(BaseModel):
    entity_id: str
    entity_type: str
    canonical_name: str
    aliases: List[str]
    team_id: str


class EventContext(BaseModel):
    previous_event: Optional[str] = None
    next_event: Optional[str] = None
    narrative: str


class HandoffEvent(BaseModel):
    clip_id: str
    time: str
    time_seconds: float
    event_type: str
    importance: float
    confidence: float
    team: Optional[str] = None
    players: List[str]
    score_after_event: str
    clip_start_sec: float
    clip_end_sec: float
    ocr_text: List[str]
    match_phase: str
    context: EventContext


class ScoreProgression(BaseModel):
    time: str
    score: str
    event: Optional[str] = None
    scorer: Optional[str] = None
    team: Optional[str] = None


class DLHandoff(BaseModel):
    """Model for D17 dl_handoff_mock.json"""
    match_context: MatchContext
    entity_registry: List[EntityRegistry]
    events: List[HandoffEvent]
    score_progression: List[ScoreProgression]
