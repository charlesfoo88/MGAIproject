# MGAI — AI-Powered Sports Highlight Generator

Automated sports match highlight reel generator using multi-agent AI pipeline with hallucination detection and video stitching. Designed to work with any sport; football is the proof-of-concept implementation.

## 🎯 Project Overview

This system generates two types of highlight reels from any sports match:
- **Reel A (Personalized)**: Tailored to user's team/player preferences
- **Reel B (Neutral)**: Balanced coverage of key match moments

Originally developed for football (soccer), the architecture is **sport-agnostic** and can adapt to basketball, tennis, American football, or any sport with timestamped event data.

**Key Features:**
- 🤖 3-stage AI agent pipeline (Analyst → Fan → Critic)
- 🧠 LLM-based query transformation for multi-entity extraction from natural language preferences
- 📚 Comprehensive knowledge base with 647 players, 20 teams, enriched metadata (DOB, manager history, stadium/competition aliases)
- 🔗 LangChain integration for prompt templating and LLM orchestration
- 🎬 Automated video extraction and stitching with ffmpeg
- 📝 LLM-generated captions with hallucination detection
- 🔍 RAG-enhanced entity verification using structured KB lookup
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
│   ├── Mock_Data/
│   ├── Models/
│   ├── Source_Videos/
│   ├── Outputs/                   # Pipeline outputs (videos, evaluation results)
│   ├── tests/                     # All test files
│   │   ├── test_pipeline.py
│   │   ├── test_transform_query.py
│   │   ├── test_search_terms_rag.py
│   │   ├── test_api.py
│   │   └── results/               # Test execution logs
│   └── baselines/                 # Baseline scripts + results
│       ├── baseline_single_prompt.py
│       ├── baseline_keyword_filter.py
│       ├── baseline_single_prompt_results.json
│       └── baseline_keyword_results.json
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

### Backend Setup

```bash
cd Backend
pip install -r requirements.txt
uvicorn main:app --reload  # Start API server at http://localhost:8000
```

See [Backend/README.md](Backend/README.md) for detailed documentation.

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
  ↓ LLM caption generation
Stage 3: Critic Agent
  ↓ Hallucination detection + re-captioning
Stage 4: Video Stitching
  ↓ Extract clips using fusion timestamps + Add captions
Output: Reel A (Personalized) + Reel B (Neutral)
```

## 📊 Data Flow

**Agent Pipeline (Stages 1-3):**
- Input: `highlight_candidates_mock.json`, `dl_handoff_mock.json`
- Output: Verified captions with entity checking

**Video Stitching (Stage 4):**
- Input: `fusion_summary.json` (ML-detected timestamps)
- Output: MP4 reels with WebVTT subtitles

## 📂 DL Pipeline Files

The MGAI agent system consumes outputs from the upstream Deep Learning pipeline:

- **D15 (highlight_candidates.json)**: Primary MGAI agent input containing ML-detected events with confidence scores, importance ratings, and initial highlight selection signals
- **D17 (dl_handoff.json)**: Primary MGAI agent input providing clean event labels, match context metadata, entity registry, and score progression
- **D14 (fusion_summary.json)**: Video stitching input referencing D3 (audio manifest) and D5 (video manifest) for precise timestamp extraction during clip assembly

These files bridge the gap between low-level ML detection and high-level narrative generation.

## 🛠️ Tech Stack

**Backend:**
- Python 3.13
- FastAPI + Uvicorn
- LangChain (prompt templates, LLM chains, output parsers)
- Groq/Gemini LLMs via LangChain integrations
- Sentence Transformers (all-MiniLM-L6-v2 for preference alignment)
- Structured Knowledge Base (JSON-based with 99.7% player DOB coverage, manager history, comprehensive aliases)
- Pydantic (data validation)
- python-dotenv (environment config)
- ffmpeg-python (video processing)
- Wikipedia API (automated KB building)

**Frontend:**
- React 18 + Vite 8
- HTML5 Video player
- Responsive CSS Grid
- RESTful API integration

## 📊 Evaluation Results

Tested across 5 different user preferences (Arsenal fan, City fan, neutral, Saka+Martinelli, De Bruyne follower):

- **Hallucination Rate**: 20% (1/5 runs flagged, automatically corrected by retry loop)
- **Average Reel A Preference Alignment Score**: 0.452 (threshold: 0.35) using all-MiniLM-L6-v2 embeddings
- **Average Pipeline Execution Time**: 28.7 seconds per run

The system successfully generated personalized and neutral highlight reels for all test cases with high preference alignment and low hallucination rates.

## 🔬 Baselines

Two baseline implementations for comparison:

**Baseline 1 — Single Prompt**:
- Approach: One Groq API call, no agents, no RAG, no hallucination check
- Time: 3.4 seconds
- Results: 9 captions generated (all Arsenal-biased, no neutral reel)
- Hallucinations detected: 3 (Martinelli nationality, goalkeeper name, "Emirates faithful" at Wembley)
- Conclusion: Fast but inaccurate, no filtering, no personalization/neutral split

**Baseline 2 — Keyword Filter**:
- Approach: No LLM, pure keyword matching on team/player names
- Time: Instant (no API calls)
- Results: Top 5 events selected by keyword overlap
- Issues: No captions generated, incorrectly includes opponent events (Haaland goal in Arsenal fan reel)
- Conclusion: Context-free, no narrative understanding

The multi-agent pipeline trades speed for accuracy, achieving 8.4x slower execution (28.7s vs 3.4s) but with robust hallucination detection, personalized/neutral splitting, and high preference alignment.

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
- `DEMO_MODE = True` - Test without video files
- `LLM_PROVIDER` - Choose "groq" or "gemini"
- `MAX_RETRIES = 2` - Re-captioning attempts
- `MAX_HIGHLIGHTS = 5` - Clips per reel
- `ALIGNMENT_THRESHOLD = 0.35` - Preference alignment cutoff

### Adding a New Match

The system is match-agnostic. To add a new match:

**MGAI Team:**
1. Update `D15_FILE_PATH` and `D17_FILE_PATH` in `config.py` to point to the new match data files
2. **Knowledge Base:** For new leagues/teams, rebuild or enrich the KB:
   - **Automated build:** Run `Tools/knowledge_base_builder.py` to fetch teams/players from football-data.org API (requires `FOOTBALL_DATA_API_KEY` in `.env`)
   - **Manual additions:** Use `Tools/add_player.py` for historical/missing players
   - **Enrichments included:** Player dateOfBirth, manager history (3 seasons), stadium aliases, competition aliases, expanded event types
   - See `Knowledge_Base_Summary.md` for full KB documentation
3. Update the `match_name` parameter in API calls

**DL Team:**
1. Run DL pipeline on the new match video → produces D14, D15, D17 JSON files
2. Confirm source video path in D5 `video_analysis_manifest.json` `source.source_path` is accessible to MGAI at runtime

No separate video file handoff needed — MGAI reads the source video path directly from D5.

## 📝 License

Educational project for SUTD MDAI program.

## 🤝 Contributing

This is a class project. For questions, contact the development team.

---

**Status:** ✅ Backend Complete | ✅ Frontend Complete | 🚀 Ready to Deploy

**Last Updated:** March 31, 2026
