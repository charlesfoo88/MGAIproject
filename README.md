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
- `GEMINI_API_KEY` (timestamp extraction, cross-modal eval)
- `GROQ_API_KEY` (pipeline agents)
- Windows: `winget install FFmpeg` | macOS: `brew install ffmpeg`

## Quick Start

**Backend:**
```bash
cd Backend
pip install -r requirements.txt
echo "GEMINI_API_KEY=your-key\nGROQ_API_KEY=your-key" > .env
python pipeline.py --match-name arsenal_5_1_man_city_2025_02_02 --all-perspectives
```

**Frontend:**
```bash
cd Frontend
npm install && npm run dev  # http://localhost:5173
```

**Backend API:**
```bash
cd Backend && python main.py  # http://localhost:8000
```

**Using the Web UI:**
- Once both servers are running, open http://localhost:5173
- Select teams, choose preference (Team or Individual player), generate reels
- View live captions, alignment scores, and reliability warnings
- See [Frontend/UI_EXPLANATION.md](Frontend/UI_EXPLANATION.md) for detailed UI behavior and features

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
