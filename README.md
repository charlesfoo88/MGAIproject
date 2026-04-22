# Personalized Sports Highlight Reel Generation

Three agents, five stages — decomposition is necessary because preference parsing, grounding, and verification cannot be collapsed into one call.

## System Capabilities

- Multi-stage pipeline: Event filtering → Prompt grounding → Generation → Verification → Output
- Personalized caption generation aligned to user preferences
- RAG-enhanced entity grounding (647 players, 20 teams)
- Hallucination detection with retry/fallback mechanism
- Disagreement challenges for low-confidence clip selections
- Auto-generates 3 perspectives per match (2 fan views + neutral)

**Tech Stack:** Python, FastAPI, React, FFmpeg, LangChain, Gemini 2.5 Flash, Groq Llama-3.3-70b, sentence-transformers

## Project Structure

```
Backend/
├── pipeline.py          # 3-reel generator
├── Agents/              # Sports Analyst, Fan, Critic
├── Tools/               # Ingestor, RAG, video stitch
├── Mock_Data/{match}/   # D15 + D17 input files
├── Outputs/{match}/     # Generated reels + logs
└── knowledge_base.json  # 647 players, 20 teams
Frontend/src/approach_b_ui/  # React UI
```

## Prerequisites

- Python 3.8+, Node.js 18+, FFmpeg
- API Keys (see Setup below):
  - `GROQ_API_KEY` - Required for pipeline agents ([Get free key](https://console.groq.com))
  - `GEMINI_API_KEY` - Required for timestamp extraction ([Get free key](https://aistudio.google.com/app/apikey))
  - `API_SPORTS_KEY` - Optional for new match data ([Get free key](https://dashboard.api-football.com/register))
- FFmpeg installation:
  - Windows: `winget install FFmpeg`
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg` or `sudo yum install ffmpeg`

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/charlesfoo88/MGAIproject.git
cd MGAIproject
```

### 2. Backend Setup
```bash
cd Backend

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env and add your API keys (GROQ_API_KEY and GEMINI_API_KEY are required)

# Test with existing match data (~45 seconds)
python pipeline.py --match-name arsenal_5_1_man_city_2025_02_02 --all-perspectives
```

### 3. Frontend Setup
```bash
cd ../Frontend

# Install dependencies
npm install

# (Optional) Copy .env.example to .env if you need to customize backend URL
cp .env.example .env

# Start development server
npm run dev  # Opens at http://localhost:5173
```

### 4. Run the Full Application

**Terminal 1 - Backend API Server:**
```bash
cd Backend
python main.py  # Runs on http://localhost:8000
```

**Terminal 2 - Frontend Dev Server:**
```bash
cd Frontend
npm run dev  # Runs on http://localhost:5173
```

**Using the Web UI:**
1. Open http://localhost:5173 in your browser
2. Select one or two teams from the dropdown
3. Choose preference type: "Team" or "Individual" (select a player)
4. Click "Generate Highlight Reel"
5. View personalized captions with alignment scores and reliability warnings
6. See [Frontend/UI_EXPLANATION.md](Frontend/UI_EXPLANATION.md) for detailed features

## System Architecture

![System Architecture Diagram](docs/archictecture%20final%20report.png)
*Three agents, five stages — Sports Analyst (filtering + grounding), Fan Agent (generation), Critic Agent (verification)*

**Data Ingestion** (pre-pipeline):
- Gemini 2.5 Flash extracts timestamps from source video
- API-Football provides match data (fixture ID, events, scores)
- Self-consistency check + regrounding if events not found
- Entity registry resolution + match context building

**Five-Stage Pipeline:**

1. **Pre-processing & Event Filtering** (Sports Analyst Agent)
   - JSON validation, user preference parsing (regex LLM query transformation)
   - Filter events by confidence threshold

2. **Ground Prompt Assembly** (Sports Analyst Agent)
   - RAG knowledge base lookup + entity resolution
   - Score progression context + assemble prompt for Fan Agent

3. **Content Generation** (Fan Agent)
   - Personalized caption generation + match recap generation

4. **Grounding & Consistency** (Critic Agent)
   - Hallucination checking + fact consistency verification
   - Preference alignment scoring + full evidence tracking
   - Retry/fallback on verification failure

5. **Output Generation**
   - Export reel home mp4 + away team mp4 + neutral mp4
   - Export VTT caption files + return captions to Frontend UI

**Disagreement Mechanism:** Critic Agent challenges clip selection between Stage 2-3, requests evidence from Sports Analyst, confirms or overrides selection.

## Pipeline Outputs (One Run, Six Key Outputs)

Per match in `Outputs/{match_name}/`:

1. **Disagreement log** (which clips were challenged and why) — Critic & Sports Analyst
2. **Match recap** paragraph (neutral summary) — Fan Agent
3. **Personalized captions** for same clips based on preference (home fan, away fan, neutral fan, home player, away player) — Fan Agent
4. **Alignment score** per caption (cosine similarity vs preference) — Critic Agent
5. **Hallucination check result** per caption (entity verification) — Critic Agent
6. **Evidence log** (full audit trail: RAG facts used, prompt, retry count) — Critic Agent

**Video Outputs:**
- `reel_{home_team}.mp4` + `.vtt` - Home team fan perspective with timed subtitles
- `reel_{away_team}.mp4` + `.vtt` - Away team fan perspective
- `reel_neutral.mp4` + `.vtt` - Neutral broadcaster perspective

---

**How to Run:**

**Generate 3 reels for existing match (~45s):**
```bash
python Backend/pipeline.py --match-name arsenal_5_1_man_city_2025_02_02 --all-perspectives
```

**Process new match:**
```bash
# Step 1: Extract timestamps from video
python Backend/Tools/approach_b_ingestor.py --match {name} --fixture-id {id} --video {file}

# Step 2: Generate 3 reels
python Backend/pipeline.py --match-name {name} --all-perspectives
```

**Run evaluation (5 test preferences):**
```bash
python Backend/evaluate.py --full
```

## Evaluation

**Metrics:**
- Alignment: Cosine similarity (user preference vs caption)
- Cross-Modal F1: Gemini Vision detection vs API-Sports ground truth
- Hallucination resolution: 100% (all retries successful)

**Baselines:** Single-prompt (no agents), template-based (rule-driven)
