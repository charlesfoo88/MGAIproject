"""
Player pool utilities for frontend dropdown hydration.

Builds a team-filtered player list from `knowledge_base.json`, then enriches with
real headshot URLs from TheSportsDB when available.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List
from urllib.parse import quote_plus
from pathlib import Path
import unicodedata

import requests

try:
    from .config import KNOWLEDGE_BASE_PATH
except ImportError:
    from config import KNOWLEDGE_BASE_PATH


SPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3"
PLACEHOLDER_HEADSHOT = "/player-headshots/player-placeholder.svg"
HEADSHOT_FIELDS = ("strCutout", "strRender", "strThumb")
FRONTEND_HEADSHOTS_DIR = KNOWLEDGE_BASE_PATH.parent.parent / "Frontend" / "public" / "player-headshots"

_team_roster_cache: Dict[str, List[dict]] = {}
_player_headshot_cache: Dict[str, str] = {}


def _norm_token(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def _slugify_player_name(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug


def _team_key(team_name: str) -> str:
    parts = re.findall(r"[a-z0-9]+", (team_name or "").lower())
    filtered = [p for p in parts if p not in {"fc", "afc", "cf", "club", "football"}]
    return "".join(filtered)


def _pick_headshot(player_row: dict) -> str:
    for field in HEADSHOT_FIELDS:
        value = str(player_row.get(field) or "").strip()
        if value:
            return value
    return ""


def _local_headshot_for_player(player_name: str) -> str:
    if not FRONTEND_HEADSHOTS_DIR.exists():
        return ""
    slug = _slugify_player_name(player_name)
    if not slug:
        return ""
    candidate = FRONTEND_HEADSHOTS_DIR / f"{slug}.svg"
    if candidate.exists():
        return f"/player-headshots/{candidate.name}"
    return ""


def _fetch_sportsdb_team_roster(team_name: str) -> List[dict]:
    key = _team_key(team_name)
    if key in _team_roster_cache:
        return _team_roster_cache[key]

    candidates = [team_name]
    if not re.search(r"\bfc\b", team_name, flags=re.IGNORECASE):
        candidates.append(f"{team_name} FC")

    results: List[dict] = []

    for candidate in candidates:
        try:
            url = f"{SPORTSDB_BASE}/searchplayers.php?t={quote_plus(candidate)}"
            response = requests.get(url, timeout=8)
            if response.status_code != 200:
                continue
            payload = response.json() if response.content else {}
            rows = payload.get("player") or []
            if not isinstance(rows, list):
                continue

            for row in rows:
                if not isinstance(row, dict):
                    continue
                name = str(row.get("strPlayer") or "").strip()
                team = str(row.get("strTeam") or team_name).strip()
                if not name:
                    continue
                results.append(
                    {
                        "name": name,
                        "team": team,
                        "headshot": _pick_headshot(row),
                        "position": str(row.get("strPosition") or "").strip(),
                        "nationality": str(row.get("strNationality") or "").strip(),
                        "source": "sportsdb_team",
                    }
                )
            if results:
                break
        except Exception:
            continue

    # De-duplicate by normalized name
    deduped: Dict[str, dict] = {}
    for row in results:
        deduped[_norm_token(row["name"])] = row

    roster = list(deduped.values())
    if roster:
        _team_roster_cache[key] = roster
    return roster


def _fetch_headshot_by_player_name(player_name: str, preferred_team: str = "") -> str:
    name_key = _norm_token(player_name)
    cache_key = f"{name_key}::{_team_key(preferred_team)}"
    if cache_key in _player_headshot_cache:
        return _player_headshot_cache[cache_key]

    headshot = ""
    try:
        url = f"{SPORTSDB_BASE}/searchplayers.php?p={quote_plus(player_name)}"
        response = requests.get(url, timeout=8)
        payload = response.json() if response.status_code == 200 and response.content else {}
        rows = payload.get("player") or []
        if isinstance(rows, list):
            exact = None
            team_matched = None
            preferred_key = _team_key(preferred_team)
            for row in rows:
                if not isinstance(row, dict):
                    continue
                row_name = str(row.get("strPlayer") or "").strip()
                if _norm_token(row_name) == name_key:
                    exact = row
                    row_team = str(row.get("strTeam") or "").strip()
                    if preferred_key and _team_key(row_team) == preferred_key:
                        team_matched = row
                        break
            chosen = team_matched or exact or (rows[0] if rows else None)
            if isinstance(chosen, dict):
                headshot = _pick_headshot(chosen)
    except Exception:
        headshot = ""

    if headshot:
        _player_headshot_cache[cache_key] = headshot
    return headshot


def _load_kb_players() -> List[dict]:
    if not KNOWLEDGE_BASE_PATH.exists():
        return []

    try:
        import json

        with open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    players = data.get("players") if isinstance(data, dict) else {}
    if not isinstance(players, dict):
        return []

    rows: List[dict] = []
    for item in players.values():
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        team = str(item.get("team") or "").strip()
        if not name or not team:
            continue
        rows.append(
            {
                "name": name,
                "team": team,
                "position": str(item.get("position") or "").strip(),
                "nationality": str(item.get("nationality") or "").strip(),
                "headshot": "",
                "source": "knowledge_base",
            }
        )
    return rows


def _normalize_team_for_output(team_name: str) -> str:
    cleaned = str(team_name or "").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s+(AFC|FC)$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _build_team_index(rows: Iterable[dict]) -> Dict[str, List[dict]]:
    index: Dict[str, List[dict]] = {}
    for row in rows:
        team_name = str(row.get("team") or "").strip()
        if not team_name:
            continue
        key = _team_key(team_name)
        if not key:
            continue
        index.setdefault(key, []).append(row)
    return index


def _resolve_team_rows(requested_team: str, team_index: Dict[str, List[dict]]) -> List[dict]:
    key = _team_key(requested_team)
    if key in team_index:
        return team_index[key]

    # Fuzzy fallback for small naming variations.
    for candidate_key, rows in team_index.items():
        if key and (key in candidate_key or candidate_key in key):
            return rows

    return []


def build_player_pool(
    teams: List[str],
    years: int = 2,
    limit_per_team: int = 60,
    require_real_headshot: bool = True,
) -> dict:
    """
    Build player pool for selected teams.

    `years` is currently metadata only. The KB already contains merged historical
    and current-season entities; this endpoint scopes that pool by selected teams.
    """
    kb_players = _load_kb_players()
    team_index = _build_team_index(kb_players)

    selected_teams = [str(team).strip() for team in teams if str(team).strip()]
    merged_rows: List[dict] = []
    skipped_missing_headshot = 0

    for requested_team in selected_teams:
        kb_rows = _resolve_team_rows(requested_team, team_index)
        roster_rows = _fetch_sportsdb_team_roster(requested_team)

        by_name: Dict[str, dict] = {}

        for row in roster_rows:
            name_key = _norm_token(row["name"])
            output_team = _normalize_team_for_output(row.get("team") or requested_team)
            by_name[name_key] = {
                **row,
                "team": output_team,
            }

        for kb_row in kb_rows:
            name_key = _norm_token(kb_row["name"])
            existing = by_name.get(name_key)
            if existing is None:
                by_name[name_key] = {
                    **kb_row,
                    "team": _normalize_team_for_output(requested_team),
                }
            else:
                # Keep richer structured metadata from KB where useful.
                if not existing.get("position") and kb_row.get("position"):
                    existing["position"] = kb_row["position"]
                if not existing.get("nationality") and kb_row.get("nationality"):
                    existing["nationality"] = kb_row["nationality"]

        team_rows = sorted(by_name.values(), key=lambda r: r["name"].lower())
        if limit_per_team > 0:
            team_rows = team_rows[:limit_per_team]

        for row in team_rows:
            headshot = str(row.get("headshot") or "").strip()
            if not headshot:
                headshot = _fetch_headshot_by_player_name(row["name"], preferred_team=requested_team)
                row["headshot"] = headshot
            if not headshot:
                headshot = _local_headshot_for_player(row["name"])
                row["headshot"] = headshot

            if require_real_headshot and not headshot:
                skipped_missing_headshot += 1
                continue

            if not headshot:
                row["headshot"] = PLACEHOLDER_HEADSHOT

            merged_rows.append(row)

    # Global de-duplication
    deduped: Dict[str, dict] = {}
    for row in merged_rows:
        key = f"{_team_key(row.get('team', ''))}:{_norm_token(row.get('name', ''))}"
        deduped[key] = row

    players = list(deduped.values())
    players.sort(key=lambda r: (str(r.get("team") or "").lower(), str(r.get("name") or "").lower()))

    return {
        "players": players,
        "meta": {
            "selected_teams": selected_teams,
            "years_requested": years,
            "limit_per_team": limit_per_team,
            "require_real_headshot": require_real_headshot,
            "total_players": len(players),
        },
        "skipped_missing_headshot": skipped_missing_headshot,
    }
