# MGAI — AI-Powered Sports Highlight Generator

Automated sports match highlight reel generator using multi-agent AI pipeline with hallucination detection and video stitching. Currently implemented for football (soccer).

## 🎯 Project Overview

This system generates **three types of highlight reels** from any sports match:
- **Reel A (Team 1 Fan)**: Enthusiastic perspective for first team (e.g., Arsenal supporter)
- **Reel B (Team 2 Fan)**: Enthusiastic perspective for second team (e.g., Man City supporter)
- **Reel C (Neutral)**: Balanced broadcaster-style coverage

Developed for football (soccer). The architecture is **sport-agnostic** in design but has only been tested and validated for football.

**Key Features:**
- 🤖 3-stage AI agent pipeline (Analyst → Fan → Critic)
- 🧠 LLM-based query transformation for multi-entity extraction from natural language preferences
- 📚 Comprehensive knowledge base with 647 players, 20 teams, enriched metadata (DOB, manager history, stadium/competition aliases)
- 🔗 LangChain integration for prompt templating and LLM orchestration
- 🎬 Automated video extraction and stitching with ffmpeg
- 📝 **Complete LLM-generated captions (10-20 words)** with hallucination detection and validation
- ⚡ **Groq-powered caption generation** (llama-3.3-70b-versatile, ~$0.0005/run) for high-quality complete sentences
- ⌨️ **Typing effect subtitles** (50 characters/second) for engaging viewer experience
- 🔍 RAG-enhanced entity verification using structured KB lookup
- 📊 Evidence tracking for caption generation (traces which D15/D17 fields and RAG facts were used)
- 🎥 Real ML timestamps from fusion analysis
- 🌐 REST API with FastAPI
- ✅ Demo mode for testing without video files

## 📁 Project Structure

```
MGAI Project/
├── README.md
├── Backend/
│   ├── config.py
│   ├── pipeline.py
│   ├── main.py
│   ├── evaluate.py
│   ├── knowledge_base.json       # Structured KB with aliases & metadata
│   ├── requirements.txt
│   ├── .env
│   ├── Agents/
│   │   ├── sports_analyst_agent.py  # Stage 1: RAG + Query Transformation
│   │   ├── fan_agent.py             # Stage 2: Caption Generation
│   │   └── critic_agent.py          # Stage 3: Hallucination Detection
│   ├── Tools/
│   ├── Schemas/
│   ├── State/
│   ├── Prompts/
│   ├── Mock_Data/                   # Organized by match name
│   │   ├── arsenal_vs_city_efl_2026/  # Mock data (default)
│   │   ├── arsenal_5_1_man_city_2025_02_02/  # Real match 1
│   │   └── liverpool_2_0_man_city_2025_02_23/ # Real match 2
│   ├── Models/
│   ├── Source_Videos/
│   ├── Outputs/                     # Organized by match name
│   │   ├── arsenal_vs_city_efl_2026/
│   │   ├── arsenal_5_1_man_city_2025_02_02/
│   │   └── liverpool_2_0_man_city_2025_02_23/
│   ├── tests/                       # All test files
│   │   ├── test_pipeline.py
│   │   ├── test_transform_query.py
│   │   ├── test_search_terms_rag.py
│   │   ├── test_api.py
│   │   └── results/                 # Organized by match name
│   │       ├── arsenal_vs_city_efl_2026/
│   │       ├── arsenal_5_1_man_city_2025_02_02/
│   │       └── liverpool_2_0_man_city_2025_02_23/
│   └── baselines/                   # Baseline scripts (results in Outputs/)
│       ├── baseline_single_prompt.py
│       └── baseline_keyword_filter.py
└── Frontend/
    ├── index.html
    ├── package.json
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── components/
        └── styles/
```

## 🚀 Quick Start

### ⚙️ Prerequisites

1. **Python 3.8+** - Verify with `python --version`

2. **FFmpeg binary** (required for video stitching):
   ```powershell
   # Windows (using winget)
   winget install FFmpeg
   
   # macOS
   brew install ffmpeg
   
   # Linux (Ubuntu/Debian)
   sudo apt install ffmpeg
   
   # Verify installation
   ffmpeg -version
   ```
   
   **Important**: FFmpeg must be in your system PATH. After installation, restart your terminal to load the updated PATH.

3. **API Keys** - Create `.env` file in `Backend/` folder:
   ```bash
   GROQ_API_KEY=your-groq-api-key-here  # Required for caption generation
   GEMINI_API_KEY=your-gemini-api-key-here  # Optional (backup LLM)
   API_SPORTS_KEY=your-api-sports-key-here  # Optional (for Approach B)
   ```

### Backend Setup

```bash
cd Backend
pip install -r requirements.txt
uvicorn main:app --reload  # Start API server at http://localhost:8000
```

See [Backend/README.md](Backend/README.md) for detailed documentation.

### Running the Pipeline

Generate all three reels for a match:

```bash
# Arsenal fan perspective
python Backend/pipeline.py --match-name arsenal_5_1_man_city_2025_02_02 --user-preference "I am an Arsenal fan and I love watching Saka play"

# Man City fan perspective  
python Backend/pipeline.py --match-name arsenal_5_1_man_city_2025_02_02 --user-preference "I am a Manchester City fan and I love watching Haaland play"

# Neutral broadcaster (auto-generated alongside personalized reel)
```

**Output** (in `Backend/Outputs/arsenal_5_1_man_city_2025_02_02/`):
- `reel_arsenal.mp4` + `reel_arsenal.vtt` (⚪🔴 Arsenal fan, enthusiastic captions)
- `reel_man_city.mp4` + `reel_man_city.vtt` (🔵⚪ Man City fan, enthusiastic captions)
- `reel_neutral.mp4` + `reel_neutral.vtt` (📺 Neutral broadcaster, factual captions)

**Export standalone subtitles** (if needed):
```bash
python Backend/Tools/export_subtitles.py
```

### Frontend Setup

```bash
cd Frontend
npm install
npm run dev  # Start Vite dev server at http://localhost:5173
```

See [Frontend/README.md](Frontend/README.md) for detailed documentation.

## 🧠 AI Pipeline Architecture

```
Stage 1: Sports Analyst Agent
  ↓ Filter highlights + RAG enrichment
Stage 2: Fan Agent
  ↓ LLM caption generation (Groq llama-3.3-70b-versatile)
  ↓ Validation: ≥8 words + punctuation, max 2 retries
Stage 3: Critic Agent
  ↓ Hallucination detection + re-captioning
Stage 4: Video Stitching
  ↓ Extract clips using fusion timestamps + Add captions with typing effect (50 CPS)
Output: 3 Reels (Team 1 Fan + Team 2 Fan + Neutral)
```

### Caption Quality
- **Length**: 10-20 words (50-90 characters)
- **Style**: Complete sentences with proper punctuation
- **Validation**: ≥8 words requirement with automated retry (max 2 attempts)
- **Examples**:
  - Arsenal fan: _"Ødegaard scores with Havertz' help, Arsenal takes the lead, **what a start, brilliant goal!**"_ (89 chars)
  - Man City fan: _"Haaland scores the equalizer for Manchester City at 55 minutes, **what a goal!**"_ (70 chars)
  - Neutral: _"E. Haaland scores the equalizer for Manchester City at 55 minutes."_ (66 chars)

## 📊 Data Flow

**Agent Pipeline (Stages 1-3):**
- Input: `Mock_Data/{ACTIVE_MATCH}/highlight_candidates.json`, `dl_handoff.json`
- Output: Verified captions with entity checking
- Results: Saved to `Outputs/{ACTIVE_MATCH}/` and `tests/results/{ACTIVE_MATCH}/`

**Video Stitching (Stage 4):**
- Input: `fusion_summary.json` (ML-detected timestamps)
- Output: MP4 reels with WebVTT subtitles

## 📂 DL Pipeline Files

The MGAI agent system supports **two data ingestion approaches** depending on upstream Deep Learning pipeline availability:

### Approach A: DL Video + Gemini Vision
**When available**: DL team provides curated highlight video (1-2 minutes)

**Input:**
- **One mp4 video file** from DL team (pre-processed, importance/confidence/emotion scored)
- **No JSON files** — MGAI extracts everything using Gemini Vision

**Workflow:**
1. MGAI receives `approach_a_{match_name}.mp4` from DL team (1-2 min curated highlights)
2. Upload video to Gemini Vision API (gemini-2.0-flash)
3. Gemini extracts ALL events by reading:
   - Scoreboard → teams, score, match clock
   - Lower third graphics → player names
   - Action → event types (goals, fouls, cards)
   - Crowd reaction → emotion levels
4. MGAI generates D15 + D17 files from Gemini Vision output
5. Pipeline runs normally → agents generate captions → video stitching

**Data flow:** DL curated video → Gemini Vision extraction → D15/D17 generation → Agent pipeline

**Status:** ⚠️ Not yet implemented (approach_a_ingestor.py needs to be built)

### Approach B: Autonomous Workflow (Current)
**When available**: Only raw 10-minute full match highlight videos (no DL preprocessing)

**Data sources:**
- **API-Sports.io**: Real-time match events (goals, cards, substitutions) via REST API
- **Gemini Vision API**: Automated timestamp detection from video frames using multimodal LLM

**Workflow:**
1. `approach_b_ingestor.py` fetches match events from API-Sports.io (14 events for Arsenal 5-1 Man City)
2. Gemini Vision 1.5 Flash analyzes video frames → maps events to precise timestamps (8/14 mapped successfully)
3. Generates **D15** (highlight_candidates.json) and **D17** (dl_handoff.json) with real data
4. MGAI agents process as normal → Video stitching extracts clips from source video

**Key advantages:**
- ✅ No dependency on DL team preprocessing
- ✅ Works with any publicly available match video
- ✅ Real match data (tested: Arsenal 5-1 Man City, Liverpool 2-0 Man City)
- ✅ Scalable to any sport with timestamped event APIs

**Schema compatibility:** Both Approach A and B generate D15/D17 files with 9 required fields + 20+ optional legacy fields for backward compatibility with original test fixtures.

**Active matches:**
- `arsenal_vs_city_efl_2026` - Mock data (original test fixture)
- `arsenal_5_1_man_city_2025_02_02` - Real match (Approach B) ✅ Full pipeline validated + RAG analysis complete
- `liverpool_2_0_man_city_2025_02_23` - Real match (Approach B) ✅ Reels generated (baseline comparison pending)
- Approach A matches - Awaiting DL team curated video delivery

## 🛠️ Tech Stack

**Backend:**
- Python 3.13
- FastAPI + Uvicorn
- LangChain (prompt templates, LLM chains, output parsers)
- **Groq API** (llama-3.3-70b-versatile for caption generation, ~$0.0005 per pipeline run)
- Gemini API (backup LLM provider)
- Sentence Transformers (all-MiniLM-L6-v2 for preference alignment)
- **Google Gemini Vision 1.5 Flash** (video timestamp detection for Approach B)
- **API-Sports.io** (real-time match event data for Approach B)
- Structured Knowledge Base (JSON-based with 99.7% player DOB coverage, manager history, **abbreviated aliases** for improved RAG matching)
- Pydantic (data validation)
- python-dotenv (environment config)
- ffmpeg-python (video processing with safe path handling for Windows)
- Wikipedia API (automated KB building)

**Frontend:**
- React 18 + Vite 8
- HTML5 Video player
- Responsive CSS Grid
- RESTful API integration

## 📊 Evaluation Results

### Arsenal 5-1 Man City (Feb 2, 2025) — RAG vs Baseline Comparison

**RAG Multi-Agent Pipeline:**
- ✅ **Instruction Adherence**: 100% (6/6 goals followed user preference)
- ✅ **Caption Quality**: Engaging, complete sentences (50-90 chars)
- ✅ **Factual Accuracy**: 100% (no hallucinations detected)
- ⏱️ **Speed**: 3-5 minutes per reel (multi-stage processing)
- 💰 **Cost**: ~$0.004 per run (8x baseline)
- 🔍 **Query Transformation**: Extracts structured preferences (team, players, search terms) for targeted KB lookups

**Baseline (Single Prompt):**
- ❌ **Instruction Adherence**: 0% (0/6 goals followed user preference, captioned all events)
- ⚠️ **Caption Quality**: Minimal, functional descriptions
- ✅ **Factual Accuracy**: 100% (no hallucinations)
- ⚡ **Speed**: 1.5 seconds (150x faster than RAG)
- 💰 **Cost**: ~$0.0005 per run
- ❌ **Query Transformation**: Raw string usage only (no structured extraction)

**Key Finding**: RAG provides **premium quality** with perfect instruction adherence and engaging captions, but at significant computational cost. Baseline is production-ready for speed but lacks personalization intelligence.

See [Arsenal RAG Analysis](Backend/Outputs/arsenal_5_1_man_city_2025_02_02/RAG_findings_and_results.md) for detailed comparison.

### Mock Data Evaluation (arsenal_vs_city_efl_2026)

Tested across 5 different user preferences (Arsenal fan, City fan, neutral, Saka+Martinelli, De Bruyne follower):

- **Hallucination Rate**: 20% (1/5 runs flagged, automatically corrected by retry loop)
- **Average Reel A Preference Alignment Score**: 0.452 (threshold: 0.35) using all-MiniLM-L6-v2 embeddings
- **Average Pipeline Execution Time**: 28.7 seconds per run

The system successfully generated personalized and neutral highlight reels for all test cases with high preference alignment and low hallucination rates.

## 🔬 Baselines

Two baseline implementations for comparison (both dynamically use `ACTIVE_MATCH` from config):

**Baseline 1 — Single Prompt (Fair Comparison)**:
- **Approach:** One Groq API call with same constraints as RAG (6 goal events, 10-20 word captions)
- **Time:** ~1.5 seconds (150x faster than RAG multi-agent pipeline)
- **Instruction Following:** 0% — Captions all events regardless of user preference
- **Caption Quality:** Functional but minimal (e.g., "Manchester City scores after 2 minutes")
- **Query Handling:** Uses raw preference string directly in prompt (no structured extraction)
- **Example Output:** [baseline_arsenal.json](Backend/Outputs/arsenal_5_1_man_city_2025_02_02/baseline_arsenal.json)
- **Conclusion:** Production-ready for speed, but no personalization intelligence

**Baseline 2 — Keyword Filter**:
- **Approach:** No LLM, pure keyword matching on team/player names
- **Time:** Instant (no API calls, zero cost)
- **Results:** Top 5 events selected by keyword overlap + importance score
- **Example:** Extracts keywords ["arsenal", "saka", "love"] → selects all Arsenal goals
- **No captions generated** (metadata only)
- **Conclusion:** Context-free, only matches team/player keywords, no narrative understanding

**Both baselines save results to:** `Outputs/{ACTIVE_MATCH}/baseline_*.json`

**Full comparison analysis:** [RAG_findings_and_results.md](Backend/Outputs/arsenal_5_1_man_city_2025_02_02/RAG_findings_and_results.md)

## 📋 API Endpoints

- `POST /api/run` - Execute pipeline, returns captions and event metadata
- `GET /api/status` - Check server status
- `GET /api/videos` - List generated videos
- `GET /api/videos/{reel}` - Download video file
- `GET /docs` - Interactive API documentation

**Event Metadata**: Each reel includes event objects with segment_id, event_type, team, clip_start_sec, clip_end_sec for precise timestamp and badge display.

## 🧪 Testing

```bash
cd Backend
cd tests ; python test_pipeline.py  # Test all agent stages
python evaluate.py  # Run multi-preference evaluation
python pipeline.py --match-name "test" --user-preference "I love Arsenal!"  # Test pipeline directly
```

## ⚙️ Configuration

Set in `Backend/config.py`:
- `LLM_PROVIDER` - Choose LLM provider: `"groq"` (default, llama-3.3-70b-versatile) or `"gemini"` (gemini-2.5-flash)
  - Groq: Faster, cheaper (~$0.0005/run), better caption quality
  - Gemini: Backup option, slower, more expensive
- `TYPING_SPEED_CPS` - Caption typing effect speed (default: 50 characters/second)
- `ACTIVE_MATCH` - Switch between matches (arsenal_vs_city_efl_2026, arsenal_5_1_man_city_2025_02_02, liverpool_2_0_man_city_2025_02_23)
  - Automatically updates data file paths and output folders
  - Test results saved to `tests/results/{ACTIVE_MATCH}/`
  - Evaluation/baseline results saved to `Outputs/{ACTIVE_MATCH}/`
  - Video outputs organized in match-specific folders: `Outputs/{ACTIVE_MATCH}/reel_*.mp4`
- `DEMO_MODE = True` - Test agents without video files (skips video stitching, Stage 4)
  - Set to `False` for production video generation
  - Requires FFmpeg installed and source video available
- `SOURCE_VIDEO_PATH` - Direct path to source video file (optional)

**Output files per match:**
- `reel_arsenal.mp4` / `reel_arsenal.vtt` - Team 1 fan perspective (enthusiastic)
- `reel_man_city.mp4` / `reel_man_city.vtt` - Team 2 fan perspective (enthusiastic)
- `reel_neutral.mp4` / `reel_neutral.vtt` - Neutral broadcaster (factual)
  - If set, overrides automatic video discovery
  - Fallback: Reads from D5 video_analysis_manifest.json → searches for {match_name}.mp4 → uses any .mp4 in Source_Videos/
- `LLM_PROVIDER` - Choose "groq" or "gemini"
- `MAX_RETRIES = 2` - Re-captioning attempts
- `MAX_HIGHLIGHTS = 5` - Clips per reel
- `ALIGNMENT_THRESHOLD = 0.35` - Preference alignment cutoff

### Adding a New Match

The system supports two workflows depending on data availability:

#### **Approach A: DL Video + Gemini Vision**

⚠️ **Not yet implemented** — `approach_a_ingestor.py` needs to be built.

**Planned workflow (when implemented):**

**MGAI Team:**
1. Place DL-provided video in `Source_Videos/approach_a_{match_name}.mp4`
2. Run `Tools/approach_a_ingestor.py --video-path <path_to_video>` to:
   - Upload video to Gemini Vision API
   - Extract all events (scoreboard, graphics, action, emotion)
   - Generate D15 and D17 files automatically
3. Update `ACTIVE_MATCH` in `config.py` to the new match name
4. Update knowledge base for new teams/players (see [Knowledge_Base_Summary.md](Knowledge_Base_Summary.md))
5. Run `pipeline.py` as normal

**DL Team:**
1. Run DL pipeline on raw match video → produces curated 1-2 minute highlight mp4
2. Provide `approach_a_{match_name}.mp4` to MGAI team (video only, no JSON files)

#### **Approach B: Autonomous Workflow (No DL Preprocessing)**  

✅ **Currently implemented and validated** (Arsenal 5-1 Man City, Liverpool 2-0 Man City)

**MGAI Team:**
1. Place raw match highlight video (10+ minutes) in `Source_Videos/` folder
2. Run `Tools/approach_b_ingestor.py --match-id <api_sports_id>` to:
   - Fetch real match events from API-Sports.io
   - Use Gemini Vision to map events to video timestamps
   - Generate D15 and D17 files automatically
3. Update `ACTIVE_MATCH` in `config.py` to the new match name
4. Update knowledge base if new players/teams (same as Approach A)
5. Run `pipeline.py` as normal

**No separate video file handoff needed** — MGAI reads source video path from D5 or discovers it automatically via SOURCE_VIDEO_PATH fallback logic.

## 📝 License

Educational project for SUTD MDAI program.

## 🤝 Contributing

This is a class project. For questions, contact the development team.

---

**Status:** ✅ Backend Complete | ✅ Frontend Complete | 🚀 Ready to Deploy

**Last Updated:** April 4, 2026
