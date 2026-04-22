"""
FastAPI Application for MGAI Video Highlight Pipeline

Provides REST API endpoints for generating personalized highlight reels
and serving the generated video files.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timezone
import json
import re
import sys
import os
import mimetypes

# Force UTF-8 console/file stream encoding on Windows to avoid charmap crashes
# when pipeline logs include symbols like ✓ / ✗.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Relative imports
try:
    from .pipeline import run_pipeline
    from .config import OUTPUT_PATH, DEMO_MODE, D15_FILE_PATH, D17_FILE_PATH
    from .player_pool import build_player_pool
    from .pokemon import generate_pokemon_card
except ImportError:
    # Direct execution fallback
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from pipeline import run_pipeline
    from config import OUTPUT_PATH, DEMO_MODE, D15_FILE_PATH, D17_FILE_PATH
    from player_pool import build_player_pool
    from pokemon import generate_pokemon_card


# Initialize FastAPI app
app = FastAPI(
    title="MGAI Video Highlight API",
    description="AI-powered personalized video highlight generation with LLM-based captioning",
    version="1.0.0"
)


def _demo_mode_active() -> bool:
    allow_demo = os.getenv("ALLOW_DEMO_MODE", "false").strip().lower() == "true"
    return bool(DEMO_MODE) and allow_demo

# Add CORS middleware (allow all origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class PipelineRequest(BaseModel):
    """Request model for /api/run endpoint"""
    match_name: str
    user_preference: str
    youtube_url: Optional[str] = None
    source_mode: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "match_name": "arsenal_vs_city_efl_2026",
                "user_preference": "I am an Arsenal fan and I love watching Saka play!"
            }
        }
    )


class PipelineResponse(BaseModel):
    """Response model for /api/run endpoint"""
    reel_a_path: Optional[str] = None
    reel_b_path: Optional[str] = None
    reel_a_captions: list[str]
    reel_b_captions: list[str]
    reel_a_events: list = []
    reel_b_events: list = []
    hallucination_flagged: bool
    retry_count: int
    reel_a_alignment_score: float = 0.0
    reel_b_alignment_score: float = 0.0
    preference_alignment_scores: list[float] = []
    match_recap: Optional[str] = None
    card_effigy_url: Optional[str] = None
    card_effigy_filename: Optional[str] = None
    pokemon_card_url: Optional[str] = None
    pokemon_card_filename: Optional[str] = None
    match_context: Optional[dict] = None
    status: str
    error_message: str = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reel_a_path": "Backend/Outputs/reel_a_arsenal_vs_city.mp4",
                "reel_b_path": "Backend/Outputs/reel_b_arsenal_vs_city.mp4",
                "reel_a_captions": ["Saka scores!", "Martinelli goal!"],
                "reel_b_captions": ["Goal scored at 22:30", "Penalty awarded"],
                "hallucination_flagged": False,
                "retry_count": 0,
                "status": "success"
            }
        }
    )


class StatusResponse(BaseModel):
    """Response model for /api/status endpoint"""
    status: str
    demo_mode: bool
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ready",
                "demo_mode": True
            }
        }
    )


# ============================================================================
# Startup Event
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Print startup message with API URL"""
    print("=" * 70)
    print("MGAI Video Highlight API - Starting")
    print("=" * 70)
    print(f"Demo Mode (configured): {DEMO_MODE}")
    print(f"Demo Mode (active): {_demo_mode_active()}")
    print(f"Output Path: {OUTPUT_PATH}")
    print(f"API Documentation: http://localhost:5000/docs")
    print(f"Interactive API: http://localhost:5000/redoc")
    print("=" * 70)
    print("Available Endpoints:")
    print("  POST   /api/run        - Generate highlight reels")
    print("  GET    /api/videos/{reel}  - Download video files")
    print("  GET    /api/card-effigy/{card_filename} - Download generated recap card")
    print("  GET    /api/pokemon/{card_filename} - Legacy card endpoint")
    print("  GET    /api/status     - Check API status")
    print("  GET    /api/website/feed   - Feed for website header/commentary")
    print("  GET    /api/players        - Team-filtered player pool")
    print("=" * 70)


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API welcome message"""
    return {
        "message": "MGAI Video Highlight API",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "run_pipeline": "POST /api/run",
            "get_video": "GET /api/videos/{reel}?match_name=...",
            "get_card_effigy": "GET /api/card-effigy/{card_filename}",
            "get_pokemon_card": "GET /api/pokemon/{card_filename}",
            "status": "GET /api/status",
            "website_feed": "GET /api/website/feed",
            "players": "GET /api/players?teams=Arsenal,Manchester City"
        }
    }


def _safe_read_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(str(path))
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _parse_vtt_captions(path: Path, max_items: int = 40) -> list[str]:
    """
    Extract readable caption lines from a VTT file.
    """
    if not path.exists():
        return []

    raw_lines: list[str] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("WEBVTT"):
                    continue
                if "-->" in line:
                    continue
                if line.isdigit():
                    continue
                raw_lines.append(line)
    except Exception:
        return []

    # Compress typewriter-style progressive subtitles by keeping only
    # the final line of each incremental sequence.
    compressed: list[str] = []
    previous = ""
    for line in raw_lines:
        if not previous:
            previous = line
            continue

        if line.startswith(previous):
            previous = line
            continue

        compressed.append(previous)
        previous = line
        if len(compressed) >= max_items:
            break

    if previous and len(compressed) < max_items:
        compressed.append(previous)

    return compressed[:max_items]


def _build_showcase_payload(match_name: str) -> dict:
    """
    Build a frontend-friendly payload from pre-generated reels in Outputs/{match_name}.
    """
    match_dir = OUTPUT_PATH / match_name
    if not match_dir.exists():
        raise FileNotFoundError(str(match_dir))

    mp4_files = sorted(match_dir.glob("reel_*.mp4"))
    reels = []
    for video_path in mp4_files:
        stem = video_path.stem  # reel_arsenal / reel_neutral / reel_man_city
        perspective = stem.replace("reel_", "")
        vtt_path = match_dir / f"{stem}.vtt"

        if perspective == "neutral":
            label = "Neutral Commentary"
        else:
            label = f"{perspective.replace('_', ' ').title()} Fan Perspective"

        reels.append(
            {
                "id": perspective,
                "label": label,
                "perspective": perspective,
                "video_url": f"/api/output-files/{match_name}/{video_path.name}",
                "vtt_url": f"/api/output-files/{match_name}/{vtt_path.name}" if vtt_path.exists() else None,
                "captions": _parse_vtt_captions(vtt_path),
                "video_size_mb": round(video_path.stat().st_size / (1024 * 1024), 2),
            }
        )

    return {
        "match_name": match_name,
        "reels": reels,
        "count": len(reels),
    }


def _clock_to_seconds(label: str) -> float:
    """
    Parse soccer clock labels like '55:00' or '90+2:00' into sortable seconds.
    """
    text = str(label or "").strip()
    if not text:
        return 0.0

    match = re.match(r"^(\d+)(?:\+(\d+))?:(\d{1,2})$", text)
    if not match:
        return 0.0

    base_min = int(match.group(1))
    stoppage_min = int(match.group(2) or 0)
    sec = int(match.group(3))
    total_min = base_min + stoppage_min
    return float(total_min * 60 + sec)


def _build_website_feed(d17_data: dict, d15_data: Any, limit: int) -> dict:
    match_context = d17_data.get("match_context") if isinstance(d17_data, dict) else {}
    if not isinstance(match_context, dict):
        match_context = {}

    d15_rows = d15_data if isinstance(d15_data, list) else []
    d15_lookup = {
        str(row.get("segment_id")): row
        for row in d15_rows
        if isinstance(row, dict) and row.get("segment_id") is not None
    }

    events = d17_data.get("events") if isinstance(d17_data, dict) else []
    if not isinstance(events, list):
        events = []

    # If D17 events are absent, fall back to D15 rows.
    if not events and d15_rows:
        events = d15_rows

    normalized_events = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue

        segment_id = str(
            event.get("clip_id")
            or event.get("segment_id")
            or f"segment_{index + 1:03d}"
        )
        d15_row = d15_lookup.get(segment_id, {})
        event_type = str(
            event.get("event_type")
            or event.get("predicted_event_type")
            or d15_row.get("predicted_event_type")
            or "event"
        )
        time_label = str(
            event.get("time")
            or event.get("match_time_display")
            or d15_row.get("match_time_display")
            or ""
        ).strip()
        narrative = str(
            ((event.get("context") or {}).get("narrative") if isinstance(event.get("context"), dict) else "")
            or event.get("about_summary")
            or event.get("context_summary")
            or d15_row.get("about_summary")
            or d15_row.get("context_summary")
            or f"{event_type.replace('_', ' ').title()} detected."
        ).strip()
        team = str(event.get("team") or d15_row.get("team") or "").strip()
        players = event.get("players") if isinstance(event.get("players"), list) else []
        score_after_event = str(event.get("score_after_event") or d15_row.get("score_after_event") or "").strip()
        importance = (
            d15_row.get("importance_score")
            if isinstance(d15_row, dict)
            else event.get("importance")
        )
        if importance is None:
            importance = event.get("importance")
        if importance is None:
            importance = event.get("confidence")

        time_seconds = event.get("time_seconds")
        if not isinstance(time_seconds, (int, float)):
            time_seconds = _clock_to_seconds(time_label)

        normalized_events.append(
            {
                "id": segment_id,
                "segment_id": segment_id,
                "time": time_label,
                "time_seconds": float(time_seconds),
                "event_type": event_type,
                "team": team,
                "players": players,
                "score_after_event": score_after_event,
                "importance_score": importance,
                "narrative": narrative,
            }
        )

    normalized_events.sort(key=lambda row: (row.get("time_seconds", 0.0), row.get("segment_id", "")))
    highlights = normalized_events[:limit]

    commentary = [
        {
            "id": row["id"],
            "time": row.get("time"),
            "event_type": row.get("event_type"),
            "team": row.get("team"),
            "score": row.get("score_after_event"),
            "commentary": row.get("narrative"),
        }
        for row in reversed(highlights)
    ]

    return {
        "match_context": match_context,
        "highlights": highlights,
        "commentary": commentary,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_files": {
            "d17": str(D17_FILE_PATH),
            "d15": str(D15_FILE_PATH),
        },
    }


@app.get("/api/status", response_model=StatusResponse, tags=["Status"])
async def get_status():
    """
    Check API status and configuration.
    
    Returns:
        JSON with status and demo_mode flag
    """
    return {
        "status": "ready",
        "demo_mode": _demo_mode_active()
    }


@app.get("/api/website/feed", tags=["Website"])
async def get_website_feed(
    limit: int = Query(20, ge=1, le=200, description="Maximum number of highlights to return")
):
    """
    Build website feed payload from current active match mock outputs (D17 + D15).
    """
    try:
        d17_data = _safe_read_json(D17_FILE_PATH)
        d15_data = _safe_read_json(D15_FILE_PATH)
        return _build_website_feed(d17_data, d15_data, limit)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Feed source file not found: {e}"
        )
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Feed source JSON parse failed: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build website feed: {e}"
        )


@app.get("/api/players", tags=["Players"])
async def get_players(
    teams: str = Query(..., description="Comma-separated team names"),
    years: int = Query(2, ge=1, le=5, description="Historical window in years"),
    limit_per_team: int = Query(60, ge=1, le=120, description="Maximum players per team"),
    require_real_headshot: bool = Query(True, description="Only return players with real headshots"),
):
    """
    Return a selected-team player pool for the frontend dropdown.
    """
    team_list = [piece.strip() for piece in teams.split(",") if piece.strip()]
    if not team_list:
        raise HTTPException(status_code=400, detail="At least one team must be provided.")

    try:
        return build_player_pool(
            teams=team_list,
            years=years,
            limit_per_team=limit_per_team,
            require_real_headshot=require_real_headshot,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build player pool: {e}")


@app.get("/api/showcase/{match_name}", tags=["Website"])
async def get_showcase(match_name: str):
    """
    Return pre-generated reels + VTT captions from Outputs/{match_name}.
    """
    try:
        return _build_showcase_payload(match_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Showcase folder not found: {match_name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build showcase payload: {e}")


@app.get("/api/output-files/{match_name}/{filename}", tags=["Website"])
async def get_output_file(match_name: str, filename: str):
    """
    Serve a specific output artifact (mp4/vtt/json/...) from Outputs/{match_name}.
    """
    safe_match = Path(match_name).name
    safe_file = Path(filename).name
    file_path = OUTPUT_PATH / safe_match / safe_file
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Output file not found: {safe_match}/{safe_file}")

    if file_path.suffix.lower() == ".vtt":
        media_type = "text/vtt"
    else:
        media_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(
        path=str(file_path),
        media_type=media_type or "application/octet-stream",
        filename=safe_file,
    )


@app.post("/api/run", response_model=PipelineResponse, tags=["Pipeline"])
async def run_pipeline_endpoint(request: PipelineRequest):
    """
    Run the complete MGAI pipeline to generate personalized highlight reels.
    
    This endpoint:
    1. Analyzes match events and filters by user preference
    2. Generates personalized (Reel A) and neutral (Reel B) captions
    3. Validates captions for hallucinations
    4. Stitches video clips with subtitles (if DEMO_MODE=False)
    
    Args:
        request: PipelineRequest with match_name and user_preference
    
    Returns:
        PipelineResponse with video paths, captions, and metadata
        
    Example:
        ```json
        {
            "match_name": "arsenal_vs_city_efl_2026",
            "user_preference": "I am an Arsenal fan and I love watching Saka play!"
        }
        ```
    """
    try:
        print(f"\n[API] Received pipeline request:")
        print(f"  Match: {request.match_name}")
        print(f"  Preference: {request.user_preference}")
        
        # Run the pipeline
        result = run_pipeline(
            match_name=request.match_name,
            user_preference=request.user_preference
        )

        # Always attach match context from current D17 source when available.
        try:
            d17_payload = _safe_read_json(D17_FILE_PATH)
            if isinstance(d17_payload, dict):
                result["match_context"] = d17_payload.get("match_context")
        except Exception:
            pass

        # Generate card-effigy recap card for all successful runs
        if result.get("status") == "success":
            match_context = result.get("match_context") or {}
            home_team = str(match_context.get("home_team") or "").strip()
            away_team = str(match_context.get("away_team") or "").strip()
            if home_team and away_team:
                match_title = f"{home_team} vs {away_team}"
            else:
                match_title = request.match_name
            card_meta = generate_pokemon_card(
                output_root=OUTPUT_PATH,
                match_name=request.match_name,
                match_title=match_title,
                team_a=home_team,
                team_b=away_team,
                user_preference=request.user_preference,
                reel_a_captions=result.get("reel_a_captions") or [],
                reel_b_captions=result.get("reel_b_captions") or [],
                match_recap=result.get("match_recap"),
                reel_a_events=result.get("reel_a_events") or [],
                reel_b_events=result.get("reel_b_events") or [],
                reel_a_path=result.get("reel_a_path"),
                reel_b_path=result.get("reel_b_path"),
            )
            filename = card_meta["pokemon_card_filename"]
            result["card_effigy_filename"] = filename
            result["card_effigy_url"] = f"/api/card-effigy/{filename}"
            # Backward-compatibility keys for older frontend clients.
            result["pokemon_card_filename"] = filename
            result["pokemon_card_url"] = f"/api/pokemon/{filename}"

        print(f"[API] Pipeline complete: {result['status']}")
        
        return result
        
    except Exception as e:
        print(f"[API] Error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(e)}"
        )


@app.get("/api/card-effigy/{card_filename}", tags=["Card Effigy"])
async def get_card_effigy(card_filename: str):
    """
    Download a generated card-effigy recap card SVG.
    """
    safe_name = Path(card_filename).name
    card_path = OUTPUT_PATH / "pokemon_cards" / safe_name

    if not card_path.exists():
        raise HTTPException(status_code=404, detail=f"Card file not found: {safe_name}")

    return FileResponse(
        path=str(card_path),
        media_type="image/svg+xml",
        filename=safe_name,
    )


@app.get("/api/pokemon/{card_filename}", tags=["Legacy"])
async def get_pokemon_card(card_filename: str):
    """
    Legacy alias for card download endpoint.
    """
    return await get_card_effigy(card_filename)


@app.get("/api/videos/{reel}", tags=["Videos"])
async def get_video(
    reel: str,
    match_name: str = Query(..., description="Match identifier (e.g., arsenal_vs_city_efl_2026)")
):
    """
    Download a generated video reel file.
    
    Args:
        reel: Either "reel_a" (personalized) or "reel_b" (neutral)
        match_name: Match identifier used during pipeline generation
    
    Returns:
        MP4 video file as downloadable attachment
        
    Raises:
        HTTPException: 400 if invalid reel type
        HTTPException: 404 if video file not found
        
    Example:
        GET /api/videos/reel_a?match_name=arsenal_vs_city_efl_2026
    """
    # Validate reel type
    if reel not in ["reel_a", "reel_b"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid reel type: '{reel}'. Must be 'reel_a' or 'reel_b'"
        )
    
    # Construct file path
    if _demo_mode_active():
        video_filename = f"{reel}_{match_name}_demo.mp4"
    else:
        video_filename = f"{reel}_{match_name}.mp4"
    
    video_path = OUTPUT_PATH / video_filename
    
    # Check if file exists
    if not video_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Video file not found: {video_filename}. "
                   f"Run the pipeline first with POST /api/run"
        )
    
    print(f"[API] Serving video: {video_path}")
    
    # Return video file
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=video_filename
    )


@app.get("/api/videos", tags=["Videos"])
async def list_videos():
    """
    List all available video files in the Outputs directory.
    
    Returns:
        JSON with list of available video files
    """
    try:
        # Ensure output directory exists
        if not OUTPUT_PATH.exists():
            return {"videos": [], "count": 0}
        
        # List all MP4 files
        video_files = list(OUTPUT_PATH.glob("*.mp4"))
        
        videos = [
            {
                "filename": video.name,
                "size_mb": round(video.stat().st_size / (1024 * 1024), 2),
                "url": f"/api/videos/{video.stem.split('_')[0]}_{video.stem.split('_')[1]}?match_name={'_'.join(video.stem.split('_')[2:]).replace('_demo', '')}"
            }
            for video in video_files
        ]
        
        return {
            "videos": videos,
            "count": len(videos)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list videos: {str(e)}"
        )


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "service": "MGAI Video Highlight API"
    }


# ============================================================================
# Run with uvicorn
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "=" * 70)
    print("Starting MGAI Video Highlight API Server")
    print("=" * 70)
    print("To run the server, use:")
    print("  uvicorn main:app --reload")
    print("  OR")
    print("  python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
    print("=" * 70 + "\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )
