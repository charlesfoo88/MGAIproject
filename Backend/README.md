# MGAI Backend

AI-powered video processing pipeline for generating personalized highlight reels with automated captioning and fact-checking. Provides REST API for frontend integration.

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

## Installation

### 1. Install Python Dependencies
From the `Backend` directory, run:

```powershell
pip install -r requirements.txt
```

This will install:
- **ffmpeg-python**: Python wrapper for FFmpeg video operations
- **sentence-transformers**: Semantic embeddings for preference alignment
- **numpy**: Numerical operations for embeddings
- **groq**: Groq API client for Llama models
- **google-generativeai**: Google Gemini API client
- **langchain**: LangChain core framework for prompt templates and LLM chains
- **langchain-groq**: LangChain integration for Groq
- **langchain-google-genai**: LangChain integration for Google Gemini
- **langchain-core**: LangChain core components
- **pydantic**: Data validation and schema enforcement
- **python-dotenv**: Environment variable management
- **wikipedia-api**: Wikipedia API for automated knowledge base building

### 2. Configure Environment Variables
Create a `.env` file in the `Backend/` folder with your API keys:

```bash
GROQ_API_KEY=your-groq-api-key-here
GEMINI_API_KEY=your-gemini-api-key-here
FOOTBALL_DATA_API_KEY=your-football-data-api-key-here  # Optional: for building/updating knowledge base
```

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
│                                    # 20 teams, 647 players (99.7% with DOB), 21 stadiums
│                                    # Enriched with: manager history, comprehensive aliases,
│                                    # expanded event types, player metadata
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
│   ├── video_stitch_tool.py         # ffmpeg — extract clips, concatenate, add WebVTT subtitles
│   ├── knowledge_base_builder.py    # Automated KB building from football-data.org API + Wikipedia
│   └── add_player.py                # Manual player addition script for historical/missing players
├── Schemas/
│   ├── __init__.py
│   ├── event_schema.py              # Pydantic models for D15 (HighlightCandidate) and D17 (DLHandoff)
│   ├── agent_input_schema.py        # AgentInput — Sports Analyst to Fan Agent
│   ├── agent_output_schema.py       # AgentOutput, ReelEvent — Fan Agent output
│   └── verified_output_schema.py    # VerifiedOutput — Critic Agent output with alignment scores
├── State/
│   ├── __init__.py
│   └── shared_state.py              # SharedState — persists data across all 3 agents
├── Prompts/
│   ├── caption_personalised.txt     # Fan-perspective caption prompt template
│   ├── caption_neutral.txt          # Broadcast-style neutral caption prompt template
│   └── hallucination_check.txt      # Fact-checking prompt template for Critic Agent
├── Mock_Data/
│   ├── highlight_candidates_mock.json   # D15 mock — ML signals, importance scores, emotion tags
│   ├── dl_handoff_mock.json             # D17 mock — clean event labels, match context, entity registry
│   ├── fusion_summary.json              # D14 — video stitching timestamps (references D3+D5)
│   ├── video_analysis_manifest.json     # D5 — video events, source video path
│   └── audio_analysis_manifest.json     # D3 — audio events, transcript chunks with file paths
├── Models/
│   └── all-MiniLM-L6-v2/              # Local Sentence Transformers model (90.9 MB, no internet needed)
├── Source_Videos/                      # Source match .mp4 files (path read from D5 manifest)
├── Outputs/
│   ├── evaluation_results.json         # Generated by evaluate.py — multi-preference metrics
│   └── reel_a_*.mp4 / reel_b_*.mp4   # Generated video reels (production mode)
├── tests/                              # All test files
│   ├── test_pipeline.py                # Full pipeline test (Stages 1-3)
│   ├── test_transform_query.py         # Query transformation tests
│   ├── test_search_terms_rag.py        # Search terms RAG integration tests
│   ├── test_api.py                     # API endpoint tests
│   └── results/                        # Test execution logs (timestamped .txt files)
└── baselines/                          # Baseline scripts + results
    ├── baseline_single_prompt.py       # Baseline 1: Single LLM call, no agents
    ├── baseline_keyword_filter.py      # Baseline 2: Keyword matching, no LLM
    ├── baseline_single_prompt_results.json  # Baseline 1 results
    └── baseline_keyword_results.json   # Baseline 2 results
```

## Quick Start

### Run Complete Pipeline (Production)
Generate personalized highlight reels from a match video:

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

**Baseline 1 — Single Prompt (No Agents):**
```bash
python baselines/baseline_single_prompt.py
```
- Approach: Single LLM call with all events in one prompt
- No agents, no RAG, no hallucination check
- Time: 3.4 seconds (8.4x faster)
- Detected hallucinations:
  - Martinelli nationality invented
  - Goalkeeper name invented
  - "Emirates faithful" mentioned (match at Wembley)
- No personalized/neutral split

**Baseline 2 — Keyword Filter (No LLM):**
```bash
python baselines/baseline_keyword_filter.py
```
- Approach: Pure keyword matching on team/player names
- No LLM calls
- Time: Instant
- Returns event list ranked by keyword overlap and importance score
- No captions generated
- Issues: Incorrectly includes opponent events (Haaland goal in Arsenal fan reel)

**Conclusion:**
The multi-agent pipeline trades speed for accuracy, achieving robust hallucination detection, personalized/neutral splitting, and high preference alignment at the cost of ~8x longer execution time.

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

- **DEMO_MODE**: Set to `True` for testing without video files (uses mock data)
- **LLM_PROVIDER**: Choose `"groq"` or `"gemini"` for caption generation
- **MAX_RETRIES**: Maximum re-captioning attempts (default: 2)
- **MAX_HIGHLIGHTS**: Maximum clips per reel (default: 5)
- **IMPORTANCE_THRESHOLD**: Filter events by importance score (default: 0.5)
- **MIN_CONFIDENCE**: Minimum classifier confidence to include an event (default: 0.5)
- **ALIGNMENT_THRESHOLD**: Minimum cosine similarity for Reel A preference alignment check (default: 0.35)

**Adding a New Match:**

The system is match-agnostic. To add a new match:

**MGAI Team:**
1. Update `D15_FILE_PATH` and `D17_FILE_PATH` in `config.py` to point to the new match data files
2. Add knowledge base entries to `knowledge_base.json`:
   - Add teams with aliases (under "teams" section)
   - Add players with team, position, nationality (under "players" section)
   - Add stadiums, competitions, match details
   - Use hierarchical structure for better organization
3. Update the `match_name` parameter in API calls or command-line arguments

**DL Team:**
1. Run DL pipeline on the new match video → produces D14, D15, D17 JSON files
2. Confirm source video path in D5 `video_analysis_manifest.json` `source.source_path` is accessible to MGAI at runtime

No separate video file handoff needed — MGAI reads the source video path directly from D5.

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

**D14 — fusion_summary.json:**
- **Purpose**: Precise video timestamps from cross-modal fusion analysis
- **Contents**: segment_id, time_range (start/end), confidence, importance_score
- **References**: D3 (audio_analysis_manifest.json) and D5 (video_analysis_manifest.json) by event ID
- **Used by**: video_stitch_tool.py only
- **NOT read by MGAI agents** — agents work with D15/D17 only

This separation allows:
- AI agents to work with clean, curated highlight data (D15/D17)
- Video extraction to use real ML-detected time ranges (D14 → D3/D5)
- Hybrid approach: AI-generated captions + ML-detected video segments

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
