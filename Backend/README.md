# MGAI Backend

AI-powered video processing pipeline for generating personalized highlight reels with automated captioning and hallucination detection.

## Prerequisites

**Required:**
- Python 3.8+
- FFmpeg (for video processing)
- API Keys:
  - `GEMINI_API_KEY` - For Gemini Vision timestamp extraction and cross-modal evaluation
  - `GROQ_API_KEY` - For pipeline agents, evaluation, and baseline
  - `API_SPORTS_KEY` - For API-Sports.io match data (optional)

**Install FFmpeg:**
```bash
# Windows
winget install FFmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

## Installation

```bash
cd Backend
pip install -r requirements.txt
```

**Create `.env` file:**
```bash
GEMINI_API_KEY=your-gemini-key
GROQ_API_KEY=your-groq-key
API_SPORTS_KEY=your-api-sports-key
```

## Project Structure

```
Backend/
├── config.py                    # Configuration
├── pipeline.py                  # Main orchestrator
├── evaluate.py                  # Evaluation script
├── cross_modal_eval.py          # Cross-modal validation
├── main.py                      # FastAPI REST API
├── knowledge_base.json          # RAG knowledge base (647 players, 20 teams)
├── Agents/                      # 3-stage agent pipeline
├── Tools/                       # Ingestor, RAG, video stitching, embeddings
├── Prompts/                     # LLM prompt templates
├── Schemas/                     # Pydantic data models
├── State/                       # Shared state management
├── Mock_Data/{match_name}/      # Match data (D15 + D17 files)
├── Source_Videos/               # Source match videos
├── Outputs/{match_name}/        # Generated reels + logs
├── Models/                      # Local sentence transformer model
├── tests/                       # Test scripts
└── baselines/                   # Baseline comparisons
```

## Workflow: Processing a New Match

### Step 1: Run Ingestor
**Purpose:** Fetch match data from API-Sports.io and extract timestamps using Gemini Vision.

**Time:** ~45 seconds (API fetch + Gemini Vision processing)

**Command:**
```bash
python Tools/approach_b_ingestor.py \
  --match arsenal_5_1_man_city_2025_02_02 \
  --fixture-id 12345678 \
  --video arsenal_5_1_man_city.mp4
```

**Outputs:**
- `Mock_Data/{match_name}/approach_b_highlight_candidates.json` (D15) - Event signals with timestamps
- `Mock_Data/{match_name}/approach_b_dl_handoff.json` (D17) - Match context + entity registry
- `Mock_Data/{match_name}/gemini_timestamp_mapping.json` - Gemini Vision output

### Step 2: Run Pipeline (All Perspectives)
**Purpose:** Generate 3 personalized highlight reels using multi-agent pipeline.

**Time:** ~45 seconds total (3 reels × ~15s each)

**Command:**
```bash
python pipeline.py --match-name arsenal_5_1_man_city_2025_02_02 --all-perspectives
```

**What it does:**
1. Extracts team names from D17
2. Runs pipeline 3 times:
   - Home team fan perspective
   - Away team fan perspective
   - Neutral broadcaster perspective
3. Each run: Stage 1 (Analyst) → Stage 2 (Fan) → Stage 3 (Critic) → Stage 4 (Video Stitch)

**Outputs (in `Outputs/{match_name}/`):**
- `reel_{home_team}.mp4` + `.vtt` - Home team fan reel with subtitles
- `reel_{away_team}.mp4` + `.vtt` - Away team fan reel with subtitles
- `reel_neutral.mp4` + `.vtt` - Neutral broadcaster reel
- `evidence_log_{team}.json` - RAG evidence tracking per perspective
- `disagreement_log_{team}.json` - Critic dialogue logs

**Example:**
```
Outputs/arsenal_5_1_man_city_2025_02_02/
├── reel_arsenal.mp4           # Arsenal fan (enthusiastic)
├── reel_arsenal.vtt
├── reel_manchester_city.mp4   # Man City fan (enthusiastic)
├── reel_manchester_city.vtt
├── reel_neutral.mp4           # Neutral broadcaster
├── reel_neutral.vtt
├── evidence_log_arsenal.json
└── disagreement_log_arsenal.json
```

### Step 3: Run Evaluation
**Purpose:** Test pipeline with multiple user preferences and compute alignment scores.

**Time:** ~75 seconds (5 test preferences)

**Command:**
```bash
python evaluate.py --full
```

**What it does:**
- Runs pipeline with 5 test preferences (2 team fans, 1 neutral, 2 player fans)
- Computes alignment scores using sentence transformers
- Logs execution time and success rate

**Outputs:**
- `Outputs/{match_name}/evaluation_results.json` - Alignment scores, timing, success rate

```json
{
  "match_name": "arsenal_5_1_man_city_2025_02_02",
  "tests": [
    {
      "preference": "I am an Arsenal fan...",
      "alignment_score": 0.73,
      "time_seconds": 12.4,
      "success": true
    }
  ],
  "summary": {
    "avg_alignment": 0.68,
    "success_rate": "5/5"
  }
}
```

### Step 4: Run Cross-Modal Evaluation
**Purpose:** Validate pipeline timestamps against blind Gemini Vision detection.

**Time:** ~30 seconds (blind Gemini Vision detection)

**Command:**
```bash
python cross_modal_eval.py \
  --match arsenal_5_1_man_city_2025_02_02 \
  --video arsenal_5_1_man_city.mp4
```

**What it does:**
1. Uploads video to Gemini Vision (blind - no API hints)
2. Compares detected events against API-Sports ground truth
3. Checks temporal alignment (±30s tolerance)

**Outputs:**
- `Outputs/{match_name}/cross_modal_results.json` - Precision, recall, F1, matched events

```json
{
  "precision": 0.83,
  "recall": 0.71,
  "f1_score": 0.77,
  "matched_events": 5,
  "false_positives": 1,
  "false_negatives": 2
}
```

### Step 5: Run Baseline 1
**Purpose:** Non-agentic comparison (single LLM prompt, no RAG, no hallucination check).

**Time:** ~5.5 seconds (5 test preferences, no agents)

**Command:**
```bash
python baselines/baseline_single_prompt.py
```

**What it does:**
- Single Groq API call per preference
- No multi-agent pipeline, no RAG enrichment, no critic validation
- Uses same 5 test preferences as evaluate.py

**Outputs:**
- `Outputs/{match_name}/baseline_single_prompt_results.json` - Alignment scores for comparison

```json
{
  "baseline": "single_prompt",
  "avg_alignment": 0.35,
  "avg_time": 1.1,
  "model": "llama-3.3-70b-versatile"
}
```

## Model Configuration

| Component | Model | Configuration | API Key Required |
|-----------|-------|---------------|------------------|
| **Ingestor** (Timestamp Extraction) | Gemini Vision 2.5 Pro | Hardcoded | GEMINI_API_KEY |
| **Pipeline Agents** (Analyst, Fan, Critic) | Groq Llama-3.3-70b | `.env: LLM_PROVIDER=groq` | GROQ_API_KEY |
| **Evaluate** (evaluate.py) | Groq Llama-3.3-70b | Uses Pipeline | GROQ_API_KEY |
| **Baseline 1** (baseline_single_prompt.py) | Groq Llama-3.3-70b | Hardcoded | GROQ_API_KEY |
| **Cross Modal** (cross_modal_eval.py) | Gemini 2.5 Pro | Hardcoded | GEMINI_API_KEY |
| **Sentence Transformers** (Alignment) | all-MiniLM-L6-v2 | Local model | None |

**Design Principle:**
- ✅ **Text generation** (Pipeline, Evaluate, Baseline): Uses Groq
- ✅ **Video analysis** (Ingestor, Cross Modal): Uses Gemini Vision
- ✅ **Embeddings** (Alignment scoring): Local sentence transformers

## Knowledge Base

The system uses a structured knowledge base (`knowledge_base.json`) for RAG-enhanced entity verification:

- **20 teams** with aliases, stadium info, manager history
- **647 players** with DOB (99.7% coverage), positions, nationalities
- **Comprehensive aliases:** "Gunners" → Arsenal, "KDB" → De Bruyne, "M. Ødegaard"
- **Event types:** 13 types (goals, cards, corners, saves, etc.)

See [Knowledge_Base_Summary.md](Knowledge_Base_Summary.md) for complete documentation.

## REST API

Start FastAPI server:
```bash
uvicorn main:app --reload
```

**Endpoints:**
- `POST /generate-reel` - Generate single reel
- `POST /generate-all-reels` - Generate all 3 perspectives
- `GET /health` - Health check
