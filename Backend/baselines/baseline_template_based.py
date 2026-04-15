"""
Baseline 2: Template-Based Non-LLM Approach

Fair comparison baseline against the full agentic pipeline.
Uses:
- Same match data
- Same event selection
- No LLM
- No agents
- No RAG
- No hallucination check

Usage:
    python baselines/baseline_template_based.py
"""

import sys
import json
import time
from pathlib import Path

# Setup paths for imports
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from config import ACTIVE_MATCH, D17_FILE_PATH, OUTPUT_PATH
from Tools.embedding_tool import encode, cosine_similarity

MATCH_NAME = ACTIVE_MATCH


def load_eval_preferences() -> list:
    """Load evaluation preferences from evaluation_config.json."""
    config_path = OUTPUT_PATH / ACTIVE_MATCH / "evaluation_config.json"
    if not config_path.exists():
        raise FileNotFoundError(
            f"evaluation_config.json not found at {config_path}. Run evaluate.py --full first."
        )

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    prefs = (
        config["auto_generated"]["disagreement_preferences"]
        + config["user_defined"]["disagreement_preferences"]
    )
    print(f"Loaded {len(prefs)} preferences from evaluation_config.json")
    return prefs


def load_handoff_data() -> dict:
    """Load D17 handoff data for active match."""
    with open(D17_FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def select_clips(events: list, max_clips: int = 6) -> list:
    """
    Same clip selection logic as Baseline-1.
    Importance >= 0.5 threshold, capped at max_clips.
    """
    filtered = [e for e in events if e.get("importance", 0) >= 0.5]
    sorted_events = sorted(filtered, key=lambda e: e.get("importance", 0), reverse=True)
    selected = sorted_events[:max_clips]
    print(f"  Clip selection: {len(events)} total -> {len(filtered)} above threshold -> {len(selected)} selected")
    return selected


def detect_preference_type(preference: str, home_team: str, away_team: str, all_players: set) -> dict:
    """
    Very simple rule-based preference detector.
    Player detection runs FIRST — before team — to correctly handle
    preferences like "I love watching Salah play for Liverpool" which
    contain both a player name and a team name.
    Returns:
        {
            "mode": "home_team" | "away_team" | "player" | "neutral",
            "team": str or None,
            "player": str or None
        }
    """
    p = preference.lower()

    # Player detection FIRST — longest match wins to avoid partial matches
    for player in sorted(all_players, key=len, reverse=True):
        if player and player.lower() in p:
            return {"mode": "player", "team": None, "player": player}

    # Team detection second
    if home_team.lower() in p:
        return {"mode": "home_team", "team": home_team, "player": None}
    if away_team.lower() in p:
        return {"mode": "away_team", "team": away_team, "player": None}

    return {"mode": "neutral", "team": None, "player": None}


def generate_template_caption(event: dict, preference_info: dict) -> str:
    """
    Template-based caption generation.
    Keep captions compact and factual.
    """
    event_type = event.get("event_type", "event")
    team = event.get("team", "Unknown Team")
    players = event.get("players", [])
    time_str = event.get("time", "N/A")
    score_after = event.get("score_after_event", "")
    narrative = event.get("context", {}).get("narrative", "").strip()

    scorer = players[0] if players else "A player"
    assist = players[1] if len(players) > 1 else None

    mode = preference_info["mode"]
    pref_team = preference_info["team"]
    pref_player = preference_info["player"]

    # Goal templates
    if event_type == "goal":
        if mode in ("home_team", "away_team"):
            if team == pref_team:
                if assist:
                    return f"{scorer} scores for {team} at {time_str}, assisted by {assist}. Score: {score_after}."
                return f"{scorer} scores for {team} at {time_str}. Score: {score_after}."
            else:
                return f"{team} score at {time_str} through {scorer}. Score becomes {score_after}."

        if mode == "player":
            if pref_player in players:
                return f"{pref_player} is involved in the goal at {time_str} for {team}. Score: {score_after}."
            return f"{scorer} scores for {team} at {time_str}. Score: {score_after}."

        return f"Goal for {team} at {time_str} by {scorer}. Score: {score_after}."

    # Substitution templates
    if event_type == "substitution":
        player_off = players[0] if players else "A player"
        player_on = players[1] if len(players) > 1 else "a substitute"

        if mode in ("home_team", "away_team"):
            if team == pref_team:
                return f"{player_off} makes way for {player_on} at {time_str} for {team}."
            else:
                return f"{team} make a change at {time_str} — {player_off} off, {player_on} on."

        if mode == "player":
            if pref_player and pref_player in players:
                return f"{pref_player} is substituted at {time_str} for {team}."
            return f"{player_off} substituted for {player_on} at {time_str} for {team}."

        return f"{player_off} substituted for {player_on} at {time_str} for {team}."

    # Card templates
    if event_type == "card":
        if players:
            return f"{players[0]} receives a card for {team} at {time_str}."
        return f"A card is shown to {team} at {time_str}."

    # Foul templates
    if event_type == "foul":
        if players:
            return f"Foul involving {players[0]} of {team} at {time_str}."
        return f"Foul committed by {team} at {time_str}."

    # Penalty-related templates
    if event_type in ("penalty_awarded", "penalty_goal"):
        if players:
            return f"{event_type.replace('_', ' ').title()} for {team} at {time_str}, involving {players[0]}."
        return f"{event_type.replace('_', ' ').title()} for {team} at {time_str}."

    # Fallback
    if narrative:
        return narrative
    return f"{event_type.replace('_', ' ').title()} for {team} at {time_str}."


def compute_alignment_score(captions: list, user_preference: str) -> float:
    """
    Same alignment method as Baseline-1.
    """
    if not captions:
        return 0.0

    pref_embedding = encode(user_preference)
    scores = []

    for caption in captions:
        caption_embedding = encode(caption)
        score = cosine_similarity(caption_embedding, pref_embedding)
        scores.append(score)

    return round(sum(scores) / len(scores), 3)


def run_baseline_template():
    print("=" * 80)
    print("BASELINE 2: TEMPLATE-BASED")
    print("=" * 80)
    print(f"Match: {MATCH_NAME}")
    print("No LLM | No Agents | No RAG | No Verification")
    print("=" * 80)

    preferences = load_eval_preferences()
    data = load_handoff_data()

    match_context = data["match_context"]
    all_events = data["events"]

    home_team = match_context["home_team"]
    away_team = match_context["away_team"]

    all_players = set()
    for e in all_events:
        for player in e.get("players", []):
            if player:
                all_players.add(player)

    print(f"\nLoaded {len(all_events)} events for {home_team} vs {away_team}")

    print("\nSelecting clips...")
    selected_events = select_clips(all_events)

    all_results = []

    for i, preference in enumerate(preferences, 1):
        print(f"\n[{i}/{len(preferences)}] Preference: {preference[:60]}...")
        print("-" * 80)

        start_time = time.time()

        pref_info = detect_preference_type(preference, home_team, away_team, all_players)
        captions = [generate_template_caption(event, pref_info) for event in selected_events]
        alignment_score = compute_alignment_score(captions, preference)

        pref_embedding = encode(preference)
        per_clip_scores = [
            round(cosine_similarity(encode(caption), pref_embedding), 3)
            for caption in captions
        ]

        time_taken = round(time.time() - start_time, 2)

        result = {
            "preference": preference,
            "mode_detected": pref_info["mode"],
            "team_detected": pref_info["team"],
            "player_detected": pref_info["player"],
            "captions": captions,
            "alignment_score": alignment_score,
            "per_clip_scores": per_clip_scores,
            "time_seconds": time_taken,
            "clip_count": len(captions),
            "status": "success",
        }

        all_results.append(result)

        print(f"  [OK] {len(captions)} captions in {time_taken}s")
        print(f"  Alignment score: {alignment_score:.3f}")
        print(f"  Per-clip scores: {per_clip_scores}")

    # Summary
    avg_alignment = round(
        sum(r["alignment_score"] for r in all_results) / len(all_results), 3
    ) if all_results else 0.0
    avg_time = round(
        sum(r["time_seconds"] for r in all_results) / len(all_results), 3
    ) if all_results else 0.0

    summary = {
        "baseline": "template_based",
        "match_name": MATCH_NAME,
        "avg_alignment": avg_alignment,
        "avg_time": avg_time,
        "test_count": len(all_results),
        "results": all_results,
    }

    output_path = OUTPUT_PATH / ACTIVE_MATCH / "baseline_template_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Average alignment: {avg_alignment:.3f}")
    print(f"Average time: {avg_time:.3f}s")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    run_baseline_template()