# Schema Cleanup TODO

**Created:** April 5, 2026  
**Status:** Deferred (after report completion)

---

## Problem

D15 (highlight_candidates.json) and D17 (dl_handoff.json) contain many optional fields added for backward compatibility with an old mock data format. These fields are **NOT USED** by the pipeline or any agents.

---

## Fields Actually Used by Pipeline

### D17 (dl_handoff.json) - HandoffEvent
✅ **ACTIVE FIELDS** (keep these):
- `clip_id` - Event identifier
- `time` - Match time display (e.g., "2:00")
- `event_type` - goal/card/substitution/etc.
- `importance` - Used for filtering clips
- `team` - Used in RAG lookups and narratives
- `players` - Used in RAG lookups and narratives
- `clip_start_sec` - Video extraction timestamp
- `clip_end_sec` - Video extraction timestamp
- `context.narrative` - Event description text
- `score_after_event` - Displayed for goals

**Files using these:**
- `Backend/Agents/fan_agent.py` - Lines 104-143 (clip selection)
- `Backend/Agents/sports_analyst_agent.py` - Lines 352-395 (RAG + transcript)
- `Backend/pipeline.py` - Lines 517-527 (evidence tracking)

### D15 (highlight_candidates.json) - HighlightCandidate
✅ **ACTIVE FIELDS** (keep these):
- `segment_id`
- `time_range.start`
- `time_range.end`
- `predicted_event_type`
- `importance_score`
- `confidence`
- `context_summary` - Event narrative
- `domain_inference` - "soccer_broadcast"
- `domain_confidence`

**Note:** D15 is barely used compared to D17. Pipeline primarily relies on D17 events.

---

## Legacy Fields - Mark for Removal

❌ **NEVER ACCESSED** (safe to delete in future refactor):

### From D15 HighlightCandidate:
- `modality_scores` (audio, visual, context)
- `feature_vector` (54 sub-fields: audio_peak, audio_density, audio_excitement, audio_whistle, audio_applause, audio_crowd, audio_commentary, audio_score_update, audio_celebration, audio_foul_or_penalty, audio_stoppage_review, audio_substitution, audio_injury_pause, audio_high_tension, visual_motion, visual_replay, visual_ocr, visual_face, visual_face_count, visual_positive_emotion, visual_negative_emotion, visual_surprise, context_scoreboard_visible, context_crowd_reaction, context_celebration, context_disappointment, context_stoppage_review, context_bench_reaction, context_highlight_package, context_substitution, context_injury, context_high_tension)
- `top_labels`
- `about_summary`
- `judgment_criteria`
- `prompt_template`
- `analysis_prompt`
- `dynamic_adjustments`
- `supporting_audio_event_ids`
- `supporting_video_event_ids`
- `rationale`
- `heuristic_importance_score`
- `learned_importance_score`
- `ranking_model`
- `importance_reasons`

### Supporting Classes to Remove:
- `ModalityScores` class
- `FeatureVector` class  
- `TopLabel` class
- `DynamicAdjustments` class

---

## Why These Fields Exist

Originally, the project assumed DL's video processing pipeline would provide:
- Audio analysis (crowd noise, commentary, celebration levels)
- Visual analysis (motion detection, face counting, emotion recognition)
- Multi-modal scoring for importance ranking

**Reality:** We're using API-Football + Gemini Vision instead, so these are just hardcoded placeholder values in [approach_b_ingestor.py](Backend/Tools/approach_b_ingestor.py) lines 458-542.

---

## Cleanup Plan

**Phase 1: Mark as Deprecated** ✅ DONE (April 5, 2026)
- [x] Add warning comments in `approach_b_ingestor.py`
- [x] Add warning comments in `event_schema.py`
- [x] Mark all legacy Optional fields with `# LEGACY - DO NOT USE`
- [x] Document in this file

**Phase 2: Remove Generation** (Future)
- [ ] Remove legacy field generation from `approach_b_ingestor.py` lines 458-542
- [ ] Regenerate Arsenal + Liverpool JSON files
- [ ] Verify pipeline still works

**Phase 3: Remove Schema Definitions** (Future)
- [ ] Remove Optional fields from `event_schema.py`
- [ ] Remove `ModalityScores`, `FeatureVector`, `TopLabel`, `DynamicAdjustments` classes
- [ ] Run tests to confirm no breakage

**Phase 4: Validation** (Future)
- [ ] Search codebase for any references to removed fields
- [ ] Run full pipeline on both matches
- [ ] Verify output quality unchanged

---

## File Size Impact

**Before cleanup:**
- `approach_b_highlight_candidates.json` (Arsenal): ~45 KB (6 events)
- `approach_b_dl_handoff.json` (Arsenal): ~12 KB (6 events)

**After cleanup (estimated):**
- `approach_b_highlight_candidates.json`: ~15 KB (6 events) - **67% smaller**
- `approach_b_dl_handoff.json`: ~12 KB (unchanged - no legacy fields here)

**Benefit:** Cleaner, more readable JSON files. Easier debugging.

---

## Migration Notes

When removing these fields:

1. **Backup current data** before regeneration
2. **Update schema version** in JSON files (add `"schema_version": "2.0"`)
3. **Run diff** to verify only legacy fields removed
4. **Test pipeline** on both Arsenal and Liverpool matches
5. **Check baselines** - ensure comparison still valid

---

## References

- Schema definitions: [Backend/Schemas/event_schema.py](Backend/Schemas/event_schema.py)
- Field generation: [Backend/Tools/approach_b_ingestor.py](Backend/Tools/approach_b_ingestor.py) lines 458-542
- Usage analysis: Grep search shows ZERO references to legacy fields in active code

---

**Last Updated:** April 5, 2026  
**Status:** Documented and marked. Deferred until after report completion.
