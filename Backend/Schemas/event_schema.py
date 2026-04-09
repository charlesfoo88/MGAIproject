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


# ===================================================================
# LEGACY CLASSES - NOT USED BY PIPELINE
# ===================================================================
# WARNING: These classes exist only for backward compatibility.
# DO NOT USE in new code. Mark for future removal.
# ===================================================================

class ModalityScores(BaseModel):
    """LEGACY - DO NOT USE - Placeholder for old mock data format"""
    audio: float
    visual: float
    context: float


class FeatureVector(BaseModel):
    """LEGACY - DO NOT USE - Placeholder for old mock data format (54 fields)"""
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
    """LEGACY - DO NOT USE - Placeholder for old mock data format"""
    label: str
    score: float


class DynamicAdjustments(BaseModel):
    """LEGACY - DO NOT USE - Placeholder for old mock data format"""
    score_change: Optional[float] = None
    celebration: Optional[float] = None
    crowd_peak: Optional[float] = None


class HighlightCandidate(BaseModel):
    """Model for D15 approach_b_highlight_candidates.json"""
    # Required fields (present in Approach B)
    segment_id: str
    time_range: TimeRange
    predicted_event_type: str
    confidence: float
    importance_score: float
    importance_rank: int
    context_summary: str
    domain_inference: str
    domain_confidence: float
    
    # Approach B fields - optional
    team: Optional[str] = None
    players: Optional[List[str]] = []
    emotion_tags: Optional[List[str]] = []
    
    # ===================================================================
    # LEGACY FIELDS - NOT USED BY PIPELINE
    # ===================================================================
    # WARNING: These fields exist only for backward compatibility with old
    # mock data format. NONE of these are accessed by pipeline.py, agents,
    # or any active code. DO NOT USE in new code.
    # 
    # TODO: Remove in future refactor after confirming no external dependencies
    # 
    # Fields marked for removal:
    # - modality_scores, feature_vector (54 sub-fields)
    # - top_labels, context_tags, emotion_tags (partially used)
    # - about_summary, judgment_criteria, prompt_template, analysis_prompt
    # - dynamic_adjustments, supporting_*_event_ids, rationale
    # - heuristic_importance_score, learned_importance_score
    # - ranking_model, importance_reasons
    # ===================================================================
    score_after_event: Optional[str] = None
    score_context: Optional[ScoreContext] = None
    match_phase: Optional[str] = None
    match_time_display: Optional[str] = None
    ocr_text: Optional[List[str]] = []
    modality_scores: Optional[ModalityScores] = None  # LEGACY - DO NOT USE
    feature_vector: Optional[FeatureVector] = None  # LEGACY - DO NOT USE
    top_labels: Optional[List[TopLabel]] = []  # LEGACY - DO NOT USE
    context_tags: Optional[List[str]] = []  # LEGACY - DO NOT USE
    about_summary: Optional[str] = None  # LEGACY - DO NOT USE
    judgment_criteria: Optional[List[str]] = []  # LEGACY - DO NOT USE
    prompt_template: Optional[str] = None  # LEGACY - DO NOT USE
    analysis_prompt: Optional[str] = None  # LEGACY - DO NOT USE
    dynamic_adjustments: Optional[DynamicAdjustments] = None  # LEGACY - DO NOT USE
    supporting_audio_event_ids: Optional[List[str]] = []  # LEGACY - DO NOT USE
    supporting_video_event_ids: Optional[List[str]] = []  # LEGACY - DO NOT USE
    rationale: Optional[List[str]] = []  # LEGACY - DO NOT USE
    heuristic_importance_score: Optional[float] = None  # LEGACY - DO NOT USE
    learned_importance_score: Optional[float] = None  # LEGACY - DO NOT USE
    ranking_model: Optional[str] = None  # LEGACY - DO NOT USE
    importance_reasons: Optional[List[Any]] = []  # LEGACY - DO NOT USE


# D17 DLHandoff Schema
class MatchContext(BaseModel):
    match_id: str
    competition: str
    season: str
    venue: str
    home_team: str
    away_team: str
    final_score: str
    # Optional fields - different between mock and Approach B
    video_id: Optional[str] = None
    date: Optional[str] = None
    match_date: Optional[str] = None  # Approach B uses match_date instead of date


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
    match_phase: str
    context: EventContext
    # Optional fields - may be None for non-goal events or when timestamps unavailable
    score_after_event: Optional[str] = None
    clip_start_sec: Optional[float] = None
    clip_end_sec: Optional[float] = None
    ocr_text: Optional[List[str]] = []


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
