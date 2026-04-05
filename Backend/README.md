# MGAI Backend

AI-powered video processing pipeline for generating personalized highlight reels with automated captioning and fact-checking. Provides REST API for frontend integration.

## 🔄 Data Ingestion: Approach A vs Approach B

The system supports two data ingestion workflows:

### **Approach A: DL Video + Gemini Vision**
- **Input:** ONE pre-processed mp4 video (1-2 minutes) from DL team — NO JSON files
- **Process:** MGAI uploads video to Gemini Vision → extracts all events (scoreboard, graphics, action, emotion)
- **Output:** Generates D15 (approach_a_highlight_candidates.json) + D17 (approach_a_dl_handoff.json) from Gemini extraction
- **Use case:** When DL team provides curated highlight video (importance/confidence/emotion scored)
- **Status:** ⚠️ Not yet implemented (approach_a_ingestor.py needs to be built)

### **Approach B: Autonomous Workflow (Current)**
- **Input:** Raw 10-minute match highlight videos (no DL preprocessing required)
- **Data sources:** 
  - **API-Sports.io** - Real-time match events (goals, cards, substitutions, lineup)
  - **Gemini Vision 1.5 Flash** - Automated timestamp detection from video frames using multimodal LLM
- **Workflow:**
  1. Run `Tools/approach_b_ingestor.py --match <match_name> --video <video_file> --fixture-id <api_sports_id>` to:
     - Fetch 14+ real match events from API-Sports.io
     - Analyze video with Gemini Vision → map events to timestamps (success rate varies)
     - Generate D15 + D17 files with real data (9 required + 20+ optional legacy fields)
  2. Run `pipeline.py` as normal → agents process → video stitching extracts clips
- **Use case:** When only raw match videos and public APIs available  
- **Status:** ✅ Fully validated on 2 real matches:
  - Arsenal 5-1 Man City (Feb 2, 2025): 8/14 events mapped, **RAG vs baseline analysis complete**
  - Liverpool 2-0 Man City (Feb 23, 2025): 2/2 events manually verified (Gemini Vision failed, human fallback used)
- **Key advantage:** No dependency on DL team, works with any publicly available match video

**Schema compatibility:** Both approaches generate D15/D17 files with 9 required fields + 20+ optional legacy fields for backward compatibility.

## Prerequisites

### 1. Python 3.8 or higher
Verify your Python installation:
```powershell
python --version
```

### 2. FFmpeg Binary
The video processing pipeline requires the `ffmpeg` binary to be installed on your system.

#### Windows Installation:
**Option A: Using winget (Windows 10/11)**
```powershell
winget install FFmpeg
```

**Option B: Using Chocolatey**
```powershell
choco install ffmpeg
```

**Option C: Manual Installation**
1. Download from https://github.com/BtbN/FFmpeg-Builds/releases
2. Extract to `C:\ffmpeg`
3. Add `C:\ffmpeg\bin` to your PATH environment variable

#### macOS Installation:
```bash
brew install ffmpeg
```

#### Linux Installation:
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg
```

#### Verify FFmpeg Installation:
```bash
ffmpeg -version
```

**Note for Windows users:** The video stitching tool includes `safe=0` flag for FFmpeg concat demuxer to handle Windows short paths (e.g., CHARLE~2). This is automatically configured in `video_stitch_tool.py`.

## Installation

### 1. Install Python Dependencies
From the `Backend` directory, run:

```powershell
pip install -r requirements.txt
```

This will install:
- **ffmpeg-python**: Python wrapper for FFmpeg video operations (includes safe=0 flag for Windows path compatibility)
- **sentence-transformers**: Semantic embeddings for preference alignment
- **numpy**: Numerical operations for embeddings
- **groq**: Groq API client for Llama models
- **google-generativeai**: Google Gemini API client (includes Vision 1.5 Flash for Approach B)
- **langchain**: LangChain core framework for prompt templates and LLM chains
- **langchain-groq**: LangChain integration for Groq
- **langchain-google-genai**: LangChain integration for Google Gemini
- **langchain-core**: LangChain core components
- **pydantic**: Data validation and schema enforcement
- **python-dotenv**: Environment variable management
- **wikipedia-api**: Wikipedia API for automated knowledge base building
- **requests**: HTTP client for API-Sports.io integration (Approach B)

### 2. Configure Environment Variables
Create a `.env` file in the `Backend/` folder with your API keys:

```bash
# Caption Generation LLM (choose one or both)
LLM_PROVIDER=groq  # Default: "groq" (faster, cheaper, better quality) or "gemini"
GROQ_API_KEY=your-groq-api-key-here  # Required for Groq (llama-3.3-70b-versatile)
GEMINI_API_KEY=your-gemini-api-key-here  # Optional: backup LLM (gemini-2.5-flash)

# Required for Approach B (autonomous workflow)
API_SPORTS_KEY=your-api-sports-io-key-here  # Get from https://api-sports.io/

# Optional: For building/updating knowledge base
FOOTBALL_DATA_API_KEY=your-football-data-api-key-here
```

**LLM Provider Comparison:**
- **Groq (Recommended)**: llama-3.3-70b-versatile
  - ✅ Faster inference (~2-3s per caption batch)
  - ✅ Better caption quality (50-90 char complete sentences)
  - ✅ Cheaper (~$0.0005 per pipeline run)
  - ✅ Reliable validation pass rate (8+ words requirement)
- **Gemini**: gemini-2.5-flash
  - ⚠️ Slower inference
  - ⚠️ Occasionally incomplete captions
  - ⚠️ More expensive
  - ✅ Good as backup option

**Note:** No need to manually set environment variables in your terminal. The application reads from the `.env` file automatically using python-dotenv.

## Project Structure

```
Backend/
├── config.py                        # All configurable values and file paths
├── pipeline.py                      # Orchestrator — runs all 3 agents in sequence
├── main.py                          # FastAPI server — REST API endpoints
├── test_api.py                      # API endpoint tests
├── evaluate.py                      # Evaluation script — 5 test preferences, logs metrics
├── knowledge_base.json              # Structured RAG knowledge base (2.5MB)
│                                    # 20 teams, 647 players (645 with DOB = 99.7% coverage)
│                                    # Enriched with: manager history, comprehensive aliases,
│                                    # **abbreviated aliases** (M. Ødegaard, B. Saka, K. Havertz),
│                                    # expanded event types, player metadata (position, nationality, DOB)
│                                    # See Knowledge_Base_Summary.md for full documentation
├── Knowledge_Base_Summary.md        # Knowledge base documentation and maintenance guide
├── requirements.txt                 # Python dependencies
├── .env                             # API keys (GROQ_API_KEY, GEMINI_API_KEY)
├── Agents/
│   ├── __init__.py
│   ├── sports_analyst_agent.py      # Stage 1: Filter events, RAG enrichment, LLM query transformation
│   ├── fan_agent.py                 # Stage 2: Clip selection, LangChain caption generation, match recap
│   └── critic_agent.py              # Stage 3: Hallucination check, preference alignment, retry
├── Tools/
│   ├── __init__.py
│   ├── embedding_tool.py            # Sentence Transformers — encode text, cosine similarity
│   ├── rag_tool.py                  # Structured knowledge base lookup with alias support
│   ├── video_stitch_tool.py         # ffmpeg — extract clips, concatenate, add WebVTT subtitles (safe=0 flag for Windows paths)
│   ├── export_subtitles.py          # **NEW:** Extract embedded subtitles from MP4 to standalone VTT files (auto-discovers reel_*.mp4)
│   ├── approach_a_ingestor.py       # ⚠️ TO BE BUILT: Approach A data generator — Gemini Vision video extraction → D15/D17
│   ├── approach_b_ingestor.py       # **NEW:** Approach B data generator — API-Sports.io + Gemini Vision → D15/D17
│   ├── knowledge_base_builder.py    # Automated KB building from football-data.org API + Wikipedia
│   ├── add_player.py                # Manual player addition script for historical/missing players
│   └── complete_player_dob.py       # DOB enrichment script (99.7% coverage achieved)
├── Schemas/
│   ├── __init__.py
│   ├── event_schema.py              # Pydantic models for D15 (HighlightCandidate) and D17 (DLHandoff)
│   ├── agent_input_schema.py        # AgentInput — Sports Analyst to Fan Agent
│   ├── agent_output_schema.py       # AgentOutput, ReelEvent, EvidenceSource — Fan Agent output with evidence tracking
│   └── verified_output_schema.py    # VerifiedOutput, VerifiedReelEvent — Critic Agent output with alignment scores and evidence summary
├── State/
│   ├── __init__.py
│   └── shared_state.py              # SharedState — persists data across all 3 agents
├── Prompts/
│   ├── caption_personalised.txt     # Fan-perspective caption prompt template
│   ├── caption_neutral.txt          # Broadcast-style neutral caption prompt template
│   └── hallucination_check.txt      # Fact-checking prompt template for Critic Agent
│                                    # Includes permanent confirmed entities (D. Rice, Gabriel Martinelli)
├── Mock_Data/                           # Match data organized by match name
│   ├── arsenal_vs_city_efl_2026/        # Mock/test data match (original test fixture)
│   │   ├── highlight_candidates.json    # D15 — ML signals, importance scores, emotion tags
│   │   ├── dl_handoff.json              # D17 — clean event labels, match context, entity registry
│   │   ├── video_analysis_manifest.json # D5 — video events, source video path
│   │   └── audio_analysis_manifest.json # D3 — audio events, transcript chunks with file paths
│   ├── arsenal_5_1_man_city_2025_02_02/ # Real match 1 (Approach B format) ✅ Validated
│   │   ├── approach_b_highlight_candidates.json  # D15 — Generated from API-Sports + Gemini Vision
│   │   ├── approach_b_dl_handoff.json            # D17 — Generated from API-Sports + Gemini Vision
│   │   └── gemini_timestamp_mapping.json         # Gemini Vision output (8/14 events mapped)
│   └── liverpool_2_0_man_city_2025_02_23/ # Real match 2 (Approach B format) - Ready for testing
│       ├── approach_b_highlight_candidates.json
│       └── approach_b_dl_handoff.json
│   # Approach A matches (when implemented):
│   # - approach_a_highlight_candidates.json (D15 from Gemini Vision video extraction)
│   # - approach_a_dl_handoff.json (D17 from Gemini Vision video extraction)
├── Models/
│   └── all-MiniLM-L6-v2/              # Local Sentence Transformers model (90.9 MB, no internet needed)
├── Source_Videos/                      # Source match .mp4 files (path read from D5 manifest)
├── Outputs/                             # Organized by match name (nested structure)
│   ├── arsenal_vs_city_efl_2026/        # Output folder for mock match
│   │   ├── evaluation_results.json      # Generated by evaluate.py — multi-preference metrics
│   │   ├── baseline_single_prompt_results.json  # Baseline 1 results
│   │   ├── baseline_keyword_results.json        # Baseline 2 results
│   │   ├── reel_arsenal.mp4 + reel_arsenal.vtt   # Team 1 fan reel (enthusiastic, e.g., Arsenal supporter)
│   │   ├── reel_man_city.mp4 + reel_man_city.vtt # Team 2 fan reel (enthusiastic, e.g., Man City supporter)
│   │   └── reel_neutral.mp4 + reel_neutral.vtt   # Neutral broadcaster reel (factual)
│   ├── arsenal_5_1_man_city_2025_02_02/ # Output folder for real match 1 ✅ Validated
│   │   ├── baseline_single_prompt_results.json  # Baseline 1 results
│   │   ├── baseline_keyword_results.json        # Baseline 2 results
│   │   ├── reel_arsenal.mp4 + reel_arsenal.vtt   # Arsenal fan perspective (89 char captions)
│   │   ├── reel_man_city.mp4 + reel_man_city.vtt # Man City fan perspective (74 char captions)
│   │   └── reel_neutral.mp4 + reel_neutral.vtt   # Neutral broadcaster (66 char captions)
│   │   ├── reel_a.mp4                   # Generated from Approach B pipeline
│   │   ├── reel_b.mp4                   # Generated from Approach B pipeline
│   │   └── reel_test.mp4                # Standalone video stitching test
│   └── liverpool_2_0_man_city_2025_02_23/ # Output folder for real match 2
├── tests/                              # All test files
│   ├── test_pipeline.py                # Full pipeline test (Stages 1-3)
│   ├── test_transform_query.py         # Query transformation tests
│   ├── test_search_terms_rag.py        # Search terms RAG integration tests
│   ├── test_api.py                     # API endpoint tests
│   └── results/                        # Test execution logs organized by match
│       ├── arsenal_vs_city_efl_2026/   # Mock match test results
│       ├── arsenal_5_1_man_city_2025_02_02/  # Real match 1 test results
│       └── liverpool_2_0_man_city_2025_02_23/ # Real match 2 test results
└── baselines/                          # Baseline scripts (results saved to Outputs/{ACTIVE_MATCH}/)
    ├── baseline_single_prompt.py       # Baseline 1: Single LLM call, no agents
    └── baseline_keyword_filter.py      # Baseline 2: Keyword matching, no LLM
```

## Quick Start

### Generate Match Data (Approach A Only)

⚠️ **Approach A is not yet implemented.** The `approach_a_ingestor.py` script needs to be built.

**Planned workflow** (when implemented):
- Place DL-provided video in `Source_Videos/`
- Run `python Tools/approach_a_ingestor.py --video-path <path>` to extract events using Gemini Vision
- Output: D15 + D17 files in `Mock_Data/{match_name}/`

**What Gemini Vision will extract:**
- Scoreboard reading: Teams, score, match clock
- Lower third graphics: Player names
- Action analysis: Event types (goals, fouls, cards, substitutions)
- Crowd reaction: Emotion levels (high/medium/low)
- Timestamps: clip_start_sec (event - 2s) and clip_end_sec (event + 8s)

### Generate Match Data (Approach B Only)

If using **Approach B** (autonomous workflow without DL preprocessing), first generate D15/D17 files from raw match video:

```powershell
# Place raw match highlight video (10+ minutes) in Source_Videos/
# Then generate data files using API-Sports.io + Gemini Vision

cd Tools
python approach_b_ingestor.py --match-id 1203519  # Arsenal 5-1 Man City example

# Output:
# - Mock_Data/{match_name}/approach_b_highlight_candidates.json (D15)
# - Mock_Data/{match_name}/approach_b_dl_handoff.json (D17)
# - Mock_Data/{match_name}/gemini_timestamp_mapping.json (Gemini Vision raw output)

# Match ID lookup: Get from API-Sports.io fixtures endpoint
# Example: https://api-sports.io/documentation/football/v3#tag/Fixtures
```

**Notes:**
- Requires `API_SPORTS_KEY` and `GEMINI_API_KEY` in `.env`
- Automatically maps event timestamps using Gemini Vision (8/14 events typically mapped)
- Files include 9 required fields + 20+ optional legacy fields for compatibility
- Skip this step if using **Approach A** (DL-provided video workflow)

### Run Complete Pipeline (Production)

#### Option 1: Automatic 3-Perspective Generation (Recommended)
Generate all 3 perspective reels in a single command:

```powershell
python pipeline.py --match-name "liverpool_2_0_man_city_2025_02_23" --all-perspectives
```

**What it does:**
1. Automatically extracts team names from D17 match_context (home_team, away_team)
2. Runs pipeline TWICE with different perspectives:
   - Home team fan perspective → saves as `reel_{home_team}.mp4`
   - Away team fan perspective → saves as `reel_{away_team}.mp4`
3. Saves neutral reel → `reel_neutral.mp4`
4. Handles file renaming and duplicate removal automatically

**Output:**
```
Backend/Outputs/{match_name}/
├── reel_{home_team}.mp4    # Home team fan perspective (personalized)
├── reel_{away_team}.mp4    # Away team fan perspective (personalized)
└── reel_neutral.mp4        # Neutral perspective (factual)
```

**Example:**
```powershell
python pipeline.py --match-name liverpool_2_0_man_city_2025_02_23 --all-perspectives
# Generates:
# - reel_manchester_city.mp4 (home team)
# - reel_liverpool.mp4 (away team)
# - reel_neutral.mp4
```

---

#### Option 2: Single Custom Perspective
Generate personalized highlight reels with custom user preference:

```powershell
# With command-line arguments
python pipeline.py --match-name "your_match_name" --user-preference "Your team/player preference here"

# Or import in your code
python
>>> from pipeline import run_pipeline
>>> result = run_pipeline(
...     match_name="your_match_name",
...     user_preference="Your team/player preference here"
... )
>>> print(f"Reel A: {result['reel_a_path']}")
>>> print(f"Captions: {len(result['reel_a_captions'])}")
```

**What it does:**
1. Stage 1: Filters events and enriches with knowledge base facts
2. Stage 2: Generates personalized (Reel A) and neutral (Reel B) captions
3. Stage 3: Validates captions for hallucinations, re-captions if needed
4. Stage 4: Stitches video clips and embeds subtitles
5. Returns: Paths to `reel_a_{match_name}.mp4` and `reel_b_{match_name}.mp4` in `Outputs/`

**DEMO_MODE:**
- Set `DEMO_MODE = True` in config.py to test without video files
- Uses mock data from Mock_Data/ folder
- Skips video stitching (Stage 4)
- Returns mock file paths

### Run as Web API (REST Server)

Start the FastAPI server to access the pipeline via HTTP endpoints:

```powershell
# Start the API server
uvicorn main:app --reload

# Or with specific host/port
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Available Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Check API status and demo mode |
| `/api/run` | POST | Run the pipeline with match_name and user_preference |
| `/api/videos/{reel}` | GET | Download generated video file (reel_a or reel_b) |
| `/api/videos` | GET | List all available video files |
| `/docs` | GET | Interactive API documentation (Swagger UI) |
| `/redoc` | GET | Alternative API documentation (ReDoc) |

**Example API Usage:**

```bash
# Check status
curl http://localhost:8000/api/status

# Run pipeline (returns captions + event metadata)
curl -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{
    "match_name": "your_match_name",
    "user_preference": "Your team/player preference here"
  }'

# Response includes:
# - reel_a_captions / reel_b_captions: Caption strings
# - reel_a_events / reel_b_events: Event metadata (segment_id, event_type, team, timestamps)
# - hallucination_flagged: Boolean for quality issues
# - retry_count: Number of re-captioning attempts
# - reel_a_alignment_score / reel_b_alignment_score: Preference alignment scores
# - match_recap: Neutral 3-4 sentence match summary

# Download generated video
curl "http://localhost:8000/api/videos/reel_a?match_name=your_match_name" \
  -o reel_a.mp4

# List all videos
curl http://localhost:8000/api/videos
```

**Test the API:**
```powershell
# Start the server in one terminal
uvicorn main:app --reload

# Run tests in another terminal
python tests/test_pipeline.py
```

### Test Individual Tools

#### Test RAG Tool
```powershell
cd Tools
python rag_tool.py
```

### Knowledge Base Format

The system uses a comprehensive structured knowledge base for RAG-enhanced entity verification with enriched metadata:

**Structured format (knowledge_base.json):**
```json
{
  "teams": {
    "arsenal": {
      "name": "Arsenal",
      "aliases": ["Arsenal FC", "Gunners", "The Arsenal"],
      "league": "Premier League",
      "home_stadium": "Emirates Stadium",
      "manager": "Mikel Arteta",
      "manager_history": [
        {"season": "2025-26", "manager": "Mikel Arteta"},
        {"season": "2024-25", "manager": "Mikel Arteta"},
        {"season": "2023-24", "manager": "Mikel Arteta"}
      ],
      "description": "Arsenal Football Club is a professional football club..."
    }
  },
  "players": {
    "bukayo_saka": {
      "name": "Bukayo Saka",
      "aliases": ["Saka", "B. Saka"],
      "team": "Arsenal",
      "position": "Winger",
      "nationality": "England",
      "dateOfBirth": "2001-09-05",
      "description": "Bukayo Saka is an English professional footballer..."
    }
  },
  "stadiums": {
    "wembley_stadium": {
      "name": "Wembley Stadium",
      "aliases": ["Wembley", "New Wembley", "The Home of Football"],
      "city": "London",
      "country": "England",
      "description": "England's national football stadium..."
    }
  },
  "competitions": {
    "efl_cup": {
      "name": "EFL Cup",
      "aliases": ["Carabao Cup", "League Cup", "EFL"],
      "description": "An annual knockout football competition..."
    }
  },
  "event_types": {
    "goal": {"name": "Goal", "description": "A goal scored..."},
    "yellow_card": {"name": "Yellow Card", "description": "Caution shown..."},
    "red_card": {"name": "Red Card", "description": "Player sent off..."}
  }
}
```

**Built-in enrichments:**
- ✅ **Player DOB**: 645/647 players (99.7%) have dateOfBirth for age-based commentary
- ✅ **Manager history**: Current manager + 3 seasons of history for all 20 teams
- ✅ **Abbreviated aliases**: M. Ødegaard, B. Saka, K. Havertz, D. Rice, J. Stones, etc. (improved RAG matching for formal commentary)
- ✅ **Stadium aliases**: 51 total aliases (fan nicknames, historical names, acronyms)
- ✅ **Competition aliases**: 17 aliases (Prem, EPL, UCL, Carabao Cup, etc.)
- ✅ **Event types**: 13 types (goals, cards, corners, saves, offsides, shots, injuries)
- ✅ **Comprehensive aliases**: Case-insensitive lookup ("Gunners" → Arsenal, "KDB" → De Bruyne)
- ✅ **Rich metadata**: Position, nationality, team affiliation
- ✅ **Hierarchical organization**: Easy to maintain and extend

**Building/Updating the KB:**
```bash
# Full rebuild from football-data.org API + Wikipedia (includes all enrichments)
cd Tools
python knowledge_base_builder.py

# Manual additions only (for historical/missing players not in current API)
python add_player.py "Kevin De Bruyne" "Manchester City" "Midfielder" "Belgium" --note "Left club in 2026"
```

**Note:** The KB is pre-enriched. Running `knowledge_base_builder.py` will automatically include DOB, aliases, and metadata. No separate enrichment scripts needed.

See [Knowledge_Base_Summary.md](Knowledge_Base_Summary.md) for full documentation.

#### Test Video Stitch Tool
```powershell
cd Tools
python video_stitch_tool.py
```

### Import Tools in Your Code
```python
from Tools import lookup, extract_and_stitch

# RAG lookup
fact = lookup("Arsenal")

# Video stitching
events = [
    {"segment_id": "seg_1", "clip_start_sec": 10.5, "clip_end_sec": 15.2}
]
captions = {"seg_1": "Goal by Saka"}
output = extract_and_stitch("source.mp4", events, captions, "output.mp4")
```

## Testing

### Full Pipeline Test (Uses LLM APIs)
```bash
python tests/test_pipeline.py
```
Tests all 3 agents in DEMO_MODE:
- Stage 1: Sports Analyst (filtering + RAG enrichment)
- Stage 2: Fan Agent (caption generation)  
- Stage 3: Critic Agent (hallucination detection + re-captioning)

Results displayed in terminal with formatted output showing captions, alignment scores, and hallucination checks. Test results are automatically saved to `tests/results/test_result_YYYYMMDD_HHMMSS.txt` with timestamp.

### Production Pipeline Test
```bash
# Set DEMO_MODE = False in config.py first
python pipeline.py --match-name "your_match" --user-preference "Your preference"
```

### Video Stitching Test (No API Calls)
```bash
# Test video extraction, concatenation, and subtitle embedding without LLM agents
python tests/test_video_stitch_only.py
```

**What it does:**
- Tests Stage 4 (video stitching) independently without running agents
- Uses hardcoded test events and captions (no API calls, no token usage)
- Extracts 5 clips from source video → concatenates → adds WebVTT subtitles
- Output: `Outputs/{match_name}/reel_test.mp4` (~3.37 MB for 50 seconds)
- **Use case:** Validate FFmpeg installation and video processing pipeline without consuming API tokens

**Requirements:**
- FFmpeg installed and in PATH
- Source video in `Source_Videos/` folder
- Set `SOURCE_VIDEO_PATH` in config.py (optional, auto-discovers if not set)

## Evaluation and Baselines

### Testing Commands

```bash
python tests/test_pipeline.py                  # Single pipeline test
python evaluate.py                             # Multi-preference evaluation
python baselines/baseline_single_prompt.py     # Baseline 1
python baselines/baseline_keyword_filter.py    # Baseline 2
```

### Single Pipeline Test
```bash
python tests/test_pipeline.py
```
Tests all 3 agents with one user preference in DEMO_MODE. Results saved to `tests/results/test_result_YYYYMMDD_HHMMSS.txt` with timestamp.

### Multi-Preference Evaluation
```bash
python evaluate.py
```

**What it does:**
- Runs pipeline 5 times with different user preferences:
  1. Arsenal fan (Saka focus)
  2. Manchester City fan (Haaland focus)
  3. Neutral observer
  4. Saka + Martinelli follower
  5. De Bruyne follower
- Logs metrics: hallucination_flagged, retry_count, alignment scores, clip counts, execution time
- Saves results to `Outputs/evaluation_results.json`

**Example Output:**
- Hallucination Rate: 20% (1/5 runs flagged)
- Average Reel A Alignment Score: 0.452 (threshold: 0.35)
- Average Execution Time: 28.7 seconds per run

### Baseline Comparisons

**Both baselines now dynamically use `ACTIVE_MATCH` from config.py** — automatically read from the current match's D17 file and save results to `Outputs/{ACTIVE_MATCH}/`.

**Baseline 1 — Single Prompt (No Agents):**
```bash
python baselines/baseline_single_prompt.py
```
- **Approach:** Single LLM call with all events in one prompt
- **No agents, no RAG, no hallucination check**
- **Time:** ~4.5 seconds (6.4x faster than multi-agent pipeline)
- **Tokens:** ~2,000 tokens per run (Groq API)
- **Result:** 14 captions generated (one per event, including substitutions/cards)
- **Example output (arsenal_5_1_man_city_2025_02_02):**
  - Caption 1: "What a start for the Gunners. Martin Ødegaard scores the opening goal..."
  - Caption 14: "E. Nwaneri scores the fifth and final goal... And, unfortunately, Bukayo Saka didn't make a significant impact in this game..."
- **Personalization:** Mentions user preference in captions but no filtering
- **No personalized/neutral split** (generates single reel only)

**Baseline 2 — Keyword Filter (No LLM):**
```bash
python baselines/baseline_keyword_filter.py
```
- **Approach:** Pure keyword matching on team/player names
- **No LLM calls** (zero cost)
- **Time:** Instant
- **Keywords extracted:** From user preference (e.g., "arsenal", "saka", "love", "watching")
- **Result:** Ranked event list by keyword overlap + importance score
- **No captions generated** (returns metadata only)
- **Example output (arsenal_5_1_man_city_2025_02_02):**
  - Extracted keywords: ["arsenal", "love", "watching", "saka", "play"]
  - Top 5 events: All Arsenal goals (each scored 1 point for "arsenal" keyword)
  - Match score: keyword count + importance ranking
- **Limitation:** Only matches team/player keywords, doesn't understand context or player involvement

**Pipeline comparison:** [To be updated after full pipeline run on arsenal_5_1_man_city_2025_02_02]

## Pipeline Output Format

The `run_pipeline()` function returns a dictionary:

```python
{
    "reel_a_path": "Backend/Outputs/reel_a_match_name.mp4",  # Personalized reel
    "reel_b_path": "Backend/Outputs/reel_b_match_name.mp4",  # Neutral reel
    "reel_a_captions": ["Caption 1", "Caption 2", ...],      # List of captions
    "reel_b_captions": ["Caption 1", "Caption 2", ...],
    "reel_a_events": [                                        # Event metadata for Reel A
        {
            "segment_id": "seg_001",
            "event_type": "goal",
            "team": "Arsenal",
            "clip_start_sec": 45.2,
            "clip_end_sec": 55.8
        },
        ...
    ],
    "reel_b_events": [...],                                   # Event metadata for Reel B
    "hallucination_flagged": False,                          # True if issues detected
    "retry_count": 0,                                         # Number of re-captions
    "reel_a_alignment_score": 0.452,                         # Preference alignment cosine similarity
    "reel_b_alignment_score": 0.301,                         # Neutral reel alignment
    "preference_alignment_scores": [0.45, 0.42, 0.38],       # Per-caption alignment scores
    "match_recap": "City took the lead through Haaland...",  # Neutral 3-4 sentence match recap
    "status": "success",                                      # "success" or "error"
    "error_message": "..."                                    # Only if status == "error"
}
```

**Event Metadata**: Each event object includes segment_id, event_type (goal, foul, substitution, etc.), team name, and precise clip timestamps for frontend display and badge coloring.

## Configuration

Edit `config.py` to customize:

- **ACTIVE_MATCH**: Switch between matches ("arsenal_vs_city_efl_2026", "arsenal_5_1_man_city_2025_02_02", "liverpool_2_0_man_city_2025_02_23")
  - Auto-resolves D15_FILE_PATH, D17_FILE_PATH from Mock_Data/{ACTIVE_MATCH}/ folder
  - Test results saved to tests/results/{ACTIVE_MATCH}/
  - Evaluation/baseline results saved to Outputs/{ACTIVE_MATCH}/
  - Video outputs organized in match-specific folders: Outputs/{ACTIVE_MATCH}/reel_a.mp4
- **DEMO_MODE**: Set to `True` for testing without video files (uses mock data)
- **LLM_PROVIDER**: Choose `"groq"` or `"gemini"` for caption generation
- **MAX_RETRIES**: Maximum re-captioning attempts (default: 2)
- **MAX_HIGHLIGHTS**: Maximum clips per reel (default: 5)
- **IMPORTANCE_THRESHOLD**: Filter events by importance score (default: 0.5)
- **MIN_CONFIDENCE**: Minimum classifier confidence to include an event (default: 0.5)
- **ALIGNMENT_THRESHOLD**: Minimum cosine similarity for Reel A preference alignment check (default: 0.35)

**Switching Between Matches:**

To switch between available matches, edit `config.py` and uncomment the desired match:

```python
# Current active match — change this to switch matches
ACTIVE_MATCH = "arsenal_vs_city_efl_2026"  # mock data
# ACTIVE_MATCH = "arsenal_5_1_man_city_2025_02_02"  # real data match 1
# ACTIVE_MATCH = "liverpool_2_0_man_city_2025_02_23"  # real data match 2
```

This automatically updates:
- Data file paths: `D15_FILE_PATH`, `D17_FILE_PATH` from `Mock_Data/{ACTIVE_MATCH}/`
- Test results location: `tests/results/{ACTIVE_MATCH}/`
- Evaluation output: `Outputs/{ACTIVE_MATCH}/evaluation_results.json`
- Baseline output: `Outputs/{ACTIVE_MATCH}/baseline_*.json`
- Video output: `Outputs/{ACTIVE_MATCH}/reel_a.mp4` and `reel_b.mp4`

**Adding a New Match:**

The system supports two workflows:

**Approach A (DL Video + Gemini Vision):**

⚠️ **Not yet implemented** — `approach_a_ingestor.py` needs to be built.

**Planned workflow (when implemented):**

**MGAI Team:**
1. Place DL-provided video in `Source_Videos/approach_a_{match_name}.mp4`
2. Run `Tools/approach_a_ingestor.py --video-path <path_to_video>` to generate D15/D17 (TO BE BUILT)
3. Add the match name to `ACTIVE_MATCH` options in `config.py`
4. Update knowledge base for new teams/players (see [Knowledge_Base_Summary.md](Knowledge_Base_Summary.md))

**DL Team:**
1. Run DL pipeline on raw match video → produces curated 1-2 minute highlight mp4
2. Provide video file only (no JSON files needed)

**Approach B (Autonomous Workflow):**

✅ **Currently implemented and validated**

**MGAI Team:**
1. Place raw match highlight video (10+ minutes) in `Source_Videos/` folder
2. Run `Tools/approach_b_ingestor.py --match-id <api_sports_id>` to generate D15/D17
3. Update `ACTIVE_MATCH` in `config.py` to the new match name
4. Update knowledge base for new teams/players (see [Knowledge_Base_Summary.md](Knowledge_Base_Summary.md))
5. Run `pipeline.py` as normal

**Note:** No separate video file handoff needed — MGAI reads source video path from D5 or discovers it automatically via SOURCE_VIDEO_PATH fallback logic (config → D5 manifest → {match_name}.mp4 → any .mp4).

## Key Enhancements

### Query Transformation (LLM-Based Entity Extraction)

The Sports Analyst Agent (Stage 1) now uses **LLM-based query transformation** to extract structured entities from user preferences.

**Traditional Approach (Regex):**
```python
"I am an Arsenal fan and I love Saka"
→ Extracts: "Arsenal" (first match only)
```

**New Approach (LLM):**
```python
"I am an Arsenal fan and I love Saka"
→ {
    "preferred_team": "Arsenal",
    "preferred_players": ["Saka"],
    "search_terms": ["Arsenal", "Saka"]
}
```

**Benefits:**
- ✅ Multi-entity extraction ("I love Saka AND Martinelli" → extracts both players)
- ✅ Name normalization (LLM converts "Haaland" → "Erling Haaland")
- ✅ Better RAG coverage (all search_terms get KB facts retrieved)
- ✅ Structured data for downstream agents
- ✅ Fallback to regex if LLM parsing fails

**Pipeline Integration:**
```
Step 2:  Extract preferred entity (regex, backward compatible)
Step 2b: Transform query with LLM ← NEW
Step 3:  Filter events
Step 4:  Enrich with RAG using search_terms ← ENHANCED
```

**Example:**
```python
# User preference: "I love Arsenal, especially Saka and Martinelli"
# Old: Retrieves KB facts for "Arsenal" only
# New: Retrieves KB facts for "Arsenal", "Saka", "Martinelli" (3 entities)
```

**Test:**
```bash
python tests/test_transform_query.py        # Test query transformation
python tests/test_search_terms_rag.py       # Test RAG integration
```

## Data Sources

The pipeline uses different data sources for different stages:

### Agent Pipeline (Stages 1-3)

**D15 — highlight_candidates_mock.json:**
- **Purpose**: Provides ML signals for event analysis
- **Contents**: predicted_event_type, confidence, importance_score, emotion_tags, context_summary
- **Read by**: Sports Analyst Agent (Stage 1), Fan Agent (Stage 2)
- **Use case**: Importance filtering, emotion analysis, event context

**D17 — dl_handoff_mock.json:**
- **Purpose**: Provides confirmed event labels and match metadata
- **Contents**:
  - `match_context`: competition, venue, home_team, away_team, final_score
  - `entity_registry`: canonical team/player names with aliases
  - `score_progression`: timeline of all goals with scorer, team, time, score
  - `context`: narrative descriptions for each event
- **Read by**: Sports Analyst Agent (Stage 1)
- **Use case**: Entity verification, match context enrichment, narrative generation

**Output**: Generated captions with verified entities, preference alignment scores, match recap

### Video Stitching (Stage 4)

**Current System (Both Approach A & B):**
- **Direct timestamp usage**: Uses `clip_start_sec` and `clip_end_sec` from D15/D17
  - **Approach A**: Timestamps extracted by Gemini Vision from DL-curated video
  - **Approach B**: Timestamps mapped by Gemini Vision to raw match video
- **Source discovery**: 4-tier fallback logic
  1. Check `SOURCE_VIDEO_PATH` from config.py
  2. Read source path from D5 video_analysis_manifest.json
  3. Search for `{match_name}.mp4` in Source_Videos/
  4. Use any .mp4 file in Source_Videos/

**Video output structure:**
- **Match-specific folders**: `Outputs/{match_name}/reel_a.mp4` and `reel_b.mp4`
- **FFmpeg processing**: Extract clips → concatenate → add WebVTT subtitles
- **Safe path handling**: Uses `safe=0` flag for Windows short paths (CHARLE~2 compatibility)

**Legacy System (DEPRECATED):**
- **D14 — fusion_summary.json**: No longer used in current pipeline
  - Old approach used cross-modal fusion analysis with separate D3/D5 references
  - Replaced by direct Gemini Vision timestamp extraction in both approaches

This approach allows:
- AI agents to work with clean, curated highlight data (D15/D17)
- Video extraction to use Gemini Vision-provided timestamps directly
- No dependency on D14 fusion analysis or separate timestamp mapping

## Troubleshooting

### FFmpeg not found
- Make sure `ffmpeg` is in your PATH
- Close and reopen your terminal after installation
- Test with: `ffmpeg -version`

### Import errors
- Run `pip install -r requirements.txt` in the Backend directory
- Verify Python version: `python --version` (requires 3.8+)

### Sentence transformers downloading model
- **Model is now bundled**: Located in `Backend/Models/all-MiniLM-L6-v2/`
- **No internet download**: Model loads from local files (90.9 MB)
- **Deployment**: Include the entire `Models/` folder when deploying

### Model files missing
- Folder should contain 9 files in `Backend/Models/all-MiniLM-L6-v2/`:
  - config.json, config_sentence_transformers.json
  - model.safetensors (90.9 MB), modules.json
  - sentence_bert_config.json, special_tokens_map.json
  - tokenizer.json, tokenizer_config.json, vocab.txt
  - **1_Pooling/config.json** (pooling layer configuration)
- Download from: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/main

### API Key Errors
- Create a `.env` file in the `Backend/` folder with valid API keys
- Format: `GROQ_API_KEY=your_key` (no quotes, no spaces around =)
- Test with: `python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('GROQ_API_KEY'))"`

## Frontend Integration

The backend API is designed to work seamlessly with the React frontend located in `../Frontend/`.

**CORS Configuration:**
- The API allows all origins during development: `allow_origins=["*"]`
- For production, update `main.py` to specify exact frontend URL

**Required for Frontend:**
1. Backend server running at http://localhost:8000
2. DEMO_MODE = True (for testing without video files)
3. API endpoint `/api/run` accepts POST requests with:
   - `match_name`: Match identifier
   - `user_preference`: User's team/player preference

**Frontend Receives:**
- `reel_a_captions` / `reel_b_captions`: Caption strings for display
- `reel_a_events` / `reel_b_events`: Event metadata for timestamps and badges
- `hallucination_flagged`: Quality indicator
- `retry_count`: Number of re-captioning attempts
- `reel_a_alignment_score` / `reel_b_alignment_score`: Preference alignment scores (0-1 scale)
- `match_recap`: Neutral match summary

**See:**
- [Frontend README](../Frontend/README.md) for setup instructions
- [Root README](../README.md) for full project overview

## Next Steps

1. **Configure API keys** in `.env` file (GROQ_API_KEY, GEMINI_API_KEY)
2. **Test the pipeline** in DEMO_MODE: `python tests/test_pipeline.py`
3. **Update knowledge base** in `knowledge_base.json` with match facts
4. **Set DEMO_MODE = False** in `config.py` for production
5. **Run the full pipeline**: `python pipeline.py --match-name "your_match" --user-preference "Your preference"`
6. **Check outputs** in `Outputs/` folder (`reel_a_*.mp4` and `reel_b_*.mp4`)

## License

Educational project for SUTD MDAI program.
