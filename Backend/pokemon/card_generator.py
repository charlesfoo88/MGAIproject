"""
Recap card generator.

Creates a single-feature SVG recap card in Backend/Outputs/pokemon_cards and
returns metadata used by the frontend.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import base64
import html
import re
import subprocess
from typing import Iterable, Optional


def _sanitize_file_component(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value or "").strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "match"


def _extract_preference_detail(user_preference: str) -> str:
    text = str(user_preference or "")
    match = re.search(r"detail\s*:\s*([^;\n]+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "Personalized Focus"


def _first_non_empty(items: Iterable[str], fallback: str) -> str:
    for item in items:
        text = str(item or "").strip()
        if text:
            return text
    return fallback


def _next_card_number(cards_dir: Path) -> int:
    cards_dir.mkdir(parents=True, exist_ok=True)
    counter_path = cards_dir / "card_counter.txt"

    current = 0
    if counter_path.exists():
        try:
            current = int(counter_path.read_text(encoding="utf-8").strip() or "0")
        except Exception:
            current = 0

    next_value = current + 1
    counter_path.write_text(str(next_value), encoding="utf-8")
    return next_value


def _truncate_text(value: str, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _to_data_uri(image_path: Path) -> str:
    suffix = image_path.suffix.lower()
    mime = "image/png"
    if suffix in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    elif suffix == ".webp":
        mime = "image/webp"
    elif suffix == ".svg":
        mime = "image/svg+xml"

    raw = image_path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _event_snapshot_hints(events: Iterable[dict]) -> list[str]:
    hints: list[str] = []
    for event in events or []:
        if not isinstance(event, dict):
            continue
        for key in ("image_url", "screenshot_url", "frame_url", "image_path", "frame_path"):
            value = str(event.get(key) or "").strip()
            if value and value not in hints:
                hints.append(value)
    return hints


def _resolve_event_hint_to_uri(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    if lowered.startswith("data:image/") or lowered.startswith("http://") or lowered.startswith("https://"):
        return text
    candidate = Path(text)
    if candidate.exists() and candidate.is_file():
        try:
            return _to_data_uri(candidate)
        except Exception:
            return ""
    return ""


def _extract_snapshots_from_video(
    video_path: Path,
    output_frames_dir: Path,
    stamp_seconds: list[float],
    prefix: str,
) -> list[str]:
    if not video_path.exists() or not video_path.is_file():
        return []

    output_frames_dir.mkdir(parents=True, exist_ok=True)
    uris: list[str] = []
    for idx, stamp in enumerate(stamp_seconds[:4], start=1):
        out_file = output_frames_dir / f"{prefix}_{idx:02d}.png"
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{max(0.0, float(stamp)):.2f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-vf",
            "scale=716:552:force_original_aspect_ratio=increase,crop=716:552",
            str(out_file),
        ]
        try:
            completed = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            break
        if completed.returncode != 0 or not out_file.exists():
            continue
        try:
            uris.append(_to_data_uri(out_file))
        except Exception:
            continue
    return uris


def _collect_feature_images(
    cards_dir: Path,
    safe_match: str,
    reel_a_path: Optional[str],
    reel_b_path: Optional[str],
    reel_a_events: list[dict],
    reel_b_events: list[dict],
) -> list[str]:
    images: list[str] = []

    # Priority 1: if upstream ever provides screenshot/image fields, consume them.
    for hint in _event_snapshot_hints([*(reel_a_events or []), *(reel_b_events or [])]):
        uri = _resolve_event_hint_to_uri(hint)
        if uri and uri not in images:
            images.append(uri)
        if len(images) >= 4:
            return images[:4]

    # Priority 2: extract screenshots from generated reels.
    frames_dir = cards_dir / "frames" / safe_match
    reel_a_file = Path(str(reel_a_path or "")).expanduser()
    reel_b_file = Path(str(reel_b_path or "")).expanduser()

    # Reel A is the user-preferred output, so sample from this first.
    stamps_a = [1.2, 3.8, 6.4, 9.0]
    if reel_a_file.exists():
        images.extend(_extract_snapshots_from_video(reel_a_file, frames_dir, stamps_a, "reel_a"))

    if len(images) < 4 and reel_b_file.exists():
        stamps_b = [1.2, 3.6, 6.0, 8.4]
        images.extend(_extract_snapshots_from_video(reel_b_file, frames_dir, stamps_b, "reel_b"))

    # De-duplicate and cap.
    deduped: list[str] = []
    for item in images:
        if item not in deduped:
            deduped.append(item)
        if len(deduped) >= 4:
            break
    return deduped


def _discrete_values_for_frame(frame_index: int, frame_count: int) -> str:
    values = []
    for segment in range(frame_count):
        values.append("1" if segment == frame_index else "0")
    values.append(values[0])
    return ";".join(values)


def _discrete_keytimes(frame_count: int) -> str:
    return ";".join(f"{i / frame_count:.6f}" for i in range(frame_count + 1))


def generate_pokemon_card(
    output_root: Path,
    match_name: str,
    match_title: str,
    team_a: str,
    team_b: str,
    user_preference: str,
    reel_a_captions: list[str],
    reel_b_captions: list[str],
    match_recap: Optional[str],
    reel_a_events: Optional[list[dict]] = None,
    reel_b_events: Optional[list[dict]] = None,
    reel_a_path: Optional[str] = None,
    reel_b_path: Optional[str] = None,
) -> dict:
    cards_dir = output_root / "pokemon_cards"
    cards_dir.mkdir(parents=True, exist_ok=True)

    card_no = _next_card_number(cards_dir)
    safe_match = _sanitize_file_component(match_name)
    filename = f"{safe_match}_card_{card_no:06d}.svg"
    file_path = cards_dir / filename

    focus = _extract_preference_detail(user_preference)
    feature_line = _first_non_empty(
        list(reel_a_captions) + list(reel_b_captions) + [match_recap or ""],
        "Best moments auto-selected from your highlight query.",
    )
    recap_line = _first_non_empty(
        [match_recap or "", *(reel_b_captions or []), *(reel_a_captions or [])],
        "Recap pending from generated highlight output.",
    )
    feature_line = _truncate_text(feature_line, 240)
    recap_line = _truncate_text(recap_line, 420)

    matchup = " vs ".join([piece for piece in [team_a, team_b] if str(piece or "").strip()]) or "Detected Matchup"
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    feature_images = _collect_feature_images(
        cards_dir=cards_dir,
        safe_match=safe_match,
        reel_a_path=reel_a_path,
        reel_b_path=reel_b_path,
        reel_a_events=reel_a_events or [],
        reel_b_events=reel_b_events or [],
    )

    def esc(value: str) -> str:
        return html.escape(str(value or ""))

    frame_layers_svg = ""
    frame_count = len(feature_images)
    if frame_count > 0:
        key_times = _discrete_keytimes(frame_count)
        cycle_seconds = max(8, frame_count * 3)
        layers = []
        for idx, uri in enumerate(feature_images):
            values = _discrete_values_for_frame(idx, frame_count)
            layers.append(
                f"""
    <image x="92" y="306" width="716" height="552" preserveAspectRatio="xMidYMid slice" href="{esc(uri)}" clip-path="url(#featureMask)">
      <animate attributeName="opacity" values="{values}" keyTimes="{key_times}" calcMode="discrete" dur="{cycle_seconds}s" repeatCount="indefinite"/>
    </image>"""
            )
        frame_layers_svg = "".join(layers)
    else:
        frame_layers_svg = f"""
  <foreignObject x="116" y="390" width="676" height="440">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:Arial,sans-serif;font-size:32px;line-height:1.28;font-weight:700;color:#e2e8f0;">
      {esc(feature_line)}
    </div>
  </foreignObject>"""

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1300" viewBox="0 0 900 1300" role="img" aria-label="Shiny recap card">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#05080f"/>
      <stop offset="100%" stop-color="#132340"/>
    </linearGradient>
    <linearGradient id="foil" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#22d3ee" stop-opacity="0.14"/>
      <stop offset="38%" stop-color="#f472b6" stop-opacity="0.16"/>
      <stop offset="70%" stop-color="#facc15" stop-opacity="0.13"/>
      <stop offset="100%" stop-color="#60a5fa" stop-opacity="0.16"/>
    </linearGradient>
    <linearGradient id="shine" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0"/>
      <stop offset="50%" stop-color="#ffffff" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="featureMask">
      <rect x="92" y="306" width="716" height="552" rx="16"/>
    </clipPath>
  </defs>
  <rect width="900" height="1300" fill="url(#bg)"/>
  <rect width="900" height="1300" fill="url(#foil)"/>
  <rect x="24" y="24" width="852" height="1252" rx="28" fill="none" stroke="#facc15" stroke-opacity="0.7" stroke-width="5"/>
  <rect x="46" y="46" width="808" height="1208" rx="22" fill="#0b1220" fill-opacity="0.46" stroke="#93c5fd" stroke-opacity="0.28"/>

  <rect x="70" y="70" width="760" height="58" rx="14" fill="#7f1d1d" fill-opacity="0.65"/>
  <text x="88" y="108" fill="#fff1f2" font-family="Arial,sans-serif" font-size="20" font-weight="800" letter-spacing="1.4">LIMITED SHINY SOCCER CARD #{card_no:06d}</text>

  <text x="72" y="178" fill="#f8fafc" font-family="Arial,sans-serif" font-size="46" font-weight="900">MGAI FEATURE CARD</text>
  <text x="72" y="216" fill="#bfdbfe" font-family="Arial,sans-serif" font-size="24" font-weight="700">{esc(match_title)}</text>
  <text x="72" y="252" fill="#67e8f9" font-family="Arial,sans-serif" font-size="22" font-weight="700">{esc(matchup)} | Focus: {esc(focus)}</text>

  <rect x="76" y="290" width="748" height="584" rx="24" fill="#020617" fill-opacity="0.7" stroke="#7dd3fc" stroke-opacity="0.42"/>
  <rect x="92" y="306" width="716" height="552" rx="16" fill="#0f172a" stroke="#fbbf24" stroke-opacity="0.35"/>
  {frame_layers_svg}
  <rect x="-400" y="280" width="280" height="660" fill="url(#shine)" transform="rotate(14 450 650)">
    <animate attributeName="x" values="-400;980" dur="4.2s" repeatCount="indefinite"/>
  </rect>
  <text x="116" y="356" fill="#fef9c3" font-family="Arial,sans-serif" font-size="22" font-weight="800" letter-spacing="1.2">BEST MOMENTS | FEATURE SHOT</text>
  <rect x="102" y="806" width="696" height="28" rx="13" fill="#0891b2" fill-opacity="0.24" stroke="#67e8f9" stroke-opacity="0.42"/>
  <text x="116" y="825" fill="#ecfeff" font-family="Arial,sans-serif" font-size="13" font-weight="700">{esc(_truncate_text(feature_line, 118))}</text>

  <rect x="56" y="900" width="788" height="328" rx="16" fill="#020617" fill-opacity="0.66" stroke="#7dd3fc" stroke-opacity="0.26"/>
  <text x="78" y="938" fill="#fef9c3" font-family="Arial,sans-serif" font-size="20" font-weight="800" letter-spacing="1.0">MATCH STORYLINE</text>
  <foreignObject x="78" y="958" width="748" height="230">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:Arial,sans-serif;font-size:23px;line-height:1.36;font-weight:600;color:#dbeafe;">
      {esc(recap_line)}
    </div>
  </foreignObject>
  <text x="78" y="1208" fill="#94a3b8" font-family="Arial,sans-serif" font-size="14" font-weight="600">Generated: {esc(generated_at)}</text>
</svg>
"""

    file_path.write_text(svg, encoding="utf-8")

    return {
        "pokemon_card_filename": filename,
        "pokemon_card_path": file_path,
    }
