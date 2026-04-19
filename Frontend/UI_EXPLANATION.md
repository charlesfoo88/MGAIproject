# MGAI UI Explanation (Approach B)

This document explains how the current frontend UI works in `Frontend/src/approach_b_ui/App.jsx` and `badge.css`.

## 1. UI Purpose

The UI is a football-first control panel that lets a user:

- choose an input source (team matchup, YouTube link, or custom football prompt),
- choose a preference target (team or player),
- generate selected vs neutral highlight reels,
- compare live caption alignment between selected and neutral views,
- receive quality warnings from verification layers,
- and collect generated highlight cards.

## 2. Main Screen Structure

The page is split into these functional zones:

1. Top live header (`MGAI MATCHCENTER`)
- EPL score/fixture/table/highlight ticker.
- Weather broadcast widget.
- Current match highlight commentary widget.

2. Generation controls
- `Source Mode`: `Team Selection`, `YouTube Link`, or `Custom Text Prompt`.
- Contextual form fields based on source mode.
- Preference controls (`Team` or `Individual`) when applicable.
- `Generate` / `Send to Pipeline` and `Check Backend` buttons.

3. Output area
- Reel panels with video + timed caption tracking.
- Selected vs neutral commentary comparison with alignment percentages.
- Warning toasts (disagreement and hallucination checks).

4. Reel highlight cards
- Spin-to-reveal card interaction.
- Collect card into local collection.
- Persistent card collection grid.

## 3. Input Modes and Behavior

### Team Selection

- User selects home and away teams.
- UI shows team logo previews.
- Preference picker appears:
  - `Team`: choose preferred team,
  - `Individual`: choose preferred player (headshot-backed player pool).

### YouTube Link

- User enters YouTube URL.
- UI validates URL format.
- UI attempts to fetch and display the YouTube title before generation.

### Custom Text Prompt

- User provides a football prompt.
- UI tries to infer teams and preferred side from text.
- Prompt mode is football-focused in wording and guidance.

## 4. Data Flow (Showcase vs Pipeline)

### 4.1 Showcase path (known matches)

When the selected teams map to a known showcase pair, the UI uses:

- `GET /api/showcase/{match_name}`
- output files under `Backend/Outputs/{match_name}/...`

The UI then loads:

- perspective caption files (`captions_{perspective}.json`),
- targeted evidence log for selected preference (`evidence_log_{key}.json`),
- neutral evidence (`evidence_log_neutral.json`),
- `captions.json` and `full_evaluation_results.json` for score/verification context.

### Evidence log resolution

Preference resolution is filename-driven. The UI builds candidate evidence-log names in priority order based on:

- preferred team,
- preferred player,
- known aliases (e.g., Odegaard spelling variants),
- match context.

This is how selected alignment and selected cue details are tied to the correct evidence file per match.

### 4.2 Pipeline path (YouTube/custom text)

For non-showcase generation, the UI calls:

- `POST /api/run`

and renders output directly from pipeline response fields (`reel_a_*`, `reel_b_*`, recap, scores, evidence arrays).

## 5. Alignment Score Display Logic

The UI displays alignment as percentages (2 decimals).

For showcase mode, selected/neutral alignment is resolved in this priority:

1. best-matched entry from `full_evaluation_results.json` (`verifier_analysis.per_run_results`),
2. selected/neutral evidence summary scores (`summary.reel_a_alignment_score`, `summary.reel_b_alignment_score`),
3. fallback from `captions.json` aggregate fields.

For live reel caption comparison, cue-level alignment is preferred. If missing, reel-level alignment is used.

## 6. Reliability Warnings in UI

Two independent warning toasts are used:

### 6.1 Disagreement Challenge (red)

- Trigger condition: cue-level disagreement rate `>= 0.25`.
- Source: per-clip disagreement mapping merged into live cue details.
- Behavior: cue-aware and replay-aware (can retrigger after rewinding).

### 6.2 Hallucination Check (yellow)

- Trigger source: verifier/evidence `hallucination_flagged` + `unsupported_mentions`.
- Mentions are parsed into stream + segment signals (e.g., `Reel A [segment_009]`).
- Trigger condition: active timed cue matches a flagged segment.
- Behavior:
  - popup visibility lasts longer (`12s`),
  - retriggers when user rewinds and re-enters the same flagged cue.

This keeps hallucination signaling tied to the exact playback context instead of showing only once globally.

## 7. Live Caption and Cue Tracking

Each reel video emits timed active-caption updates:

- current caption text,
- current cue index.

The UI keeps selected and neutral live cues in sync for:

- on-screen live commentary,
- cue-level alignment labels,
- disagreement/hallucination warning checks.

## 8. Highlight Card System

After generation:

- user can spin once per run to pull a highlight card from the active reel set,
- rarity is weighted by highlight score,
- user can collect once per run,
- collection is persisted in local storage.

First-time bootstrap for current storage version resets old collection/inventory keys so a new user starts empty.

## 9. Key Files

- UI logic: `Frontend/src/approach_b_ui/App.jsx`
- UI styling: `Frontend/src/approach_b_ui/badge.css`
- Frontend entry: `Frontend/src/main.jsx`

