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
from typing import Optional
import sys

# Relative imports
try:
    from .pipeline import run_pipeline
    from .config import OUTPUT_PATH, DEMO_MODE
except ImportError:
    # Direct execution fallback
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from pipeline import run_pipeline
    from config import OUTPUT_PATH, DEMO_MODE


# Initialize FastAPI app
app = FastAPI(
    title="MGAI Video Highlight API",
    description="AI-powered personalized video highlight generation with LLM-based captioning",
    version="1.0.0"
)

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
    reel_a_path: str
    reel_b_path: str
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
    print(f"Demo Mode: {DEMO_MODE}")
    print(f"Output Path: {OUTPUT_PATH}")
    print(f"API Documentation: http://localhost:8000/docs")
    print(f"Interactive API: http://localhost:8000/redoc")
    print("=" * 70)
    print("Available Endpoints:")
    print("  POST   /api/run        - Generate highlight reels")
    print("  GET    /api/videos/{reel}  - Download video files")
    print("  GET    /api/status     - Check API status")
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
            "status": "GET /api/status"
        }
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
        "demo_mode": DEMO_MODE
    }


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
        
        print(f"[API] Pipeline complete: {result['status']}")
        
        return result
        
    except Exception as e:
        print(f"[API] Error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(e)}"
        )


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
    if DEMO_MODE:
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
        port=8000,
        reload=True,
        log_level="info"
    )
