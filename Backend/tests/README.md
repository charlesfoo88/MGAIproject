# Tests

## Running Tests

### Full Pipeline Test
```bash
cd tests
python test_pipeline.py
```

This will:
- Run all 3 agents (sports_analyst with LLM query transformation, fan_agent with LangChain, critic_agent)
- Test RAG knowledge base enrichment with search terms
- Make LLM API calls (requires API keys in `.env`)
- Display results to console
- Save timestamped results to `tests/results/{ACTIVE_MATCH}/test_result_YYYYMMDD_HHMMSS.txt`
  - Results organized by match (arsenal_vs_city_efl_2026, arsenal_5_1_man_city_2025_02_02, liverpool_2_0_man_city_2025_02_23)
  - Switch matches by editing `ACTIVE_MATCH` in `config.py`

### Query Transformation Tests
```bash
python tests/test_transform_query.py        # Test LLM-based multi-entity extraction from natural language
python tests/test_search_terms_rag.py       # Test search terms integration with knowledge base RAG lookup
```

These tests validate:
- Natural language preference parsing ("I love Arsenal and Saka!" → ["Arsenal", "Saka"])  
- Multi-entity extraction (teams, players, managers)
- Knowledge base lookup with extracted entities
- Alias resolution and fact retrieval

### API Tests
```bash
python tests/test_api.py                    # Test REST API endpoints
```

## Test Results

All test outputs are saved to `results/{ACTIVE_MATCH}/` folders with timestamps for easy tracking and debugging.

**Folder Organization:**
```
tests/results/
├── arsenal_vs_city_efl_2026/           # Mock match test results
│   ├── test_result_20260404_115057.txt
│   └── ... (33+ test files)
├── arsenal_5_1_man_city_2025_02_02/    # Real match 1 test results
│   └── test_result_20260404_115307.txt
└── liverpool_2_0_man_city_2025_02_23/  # Real match 2 test results
    └── test_result_20260404_115332.txt
```

**Switching Matches:**
To test a different match, edit `Backend/config.py`:
```python
# Uncomment the match you want to test
ACTIVE_MATCH = "arsenal_vs_city_efl_2026"  # mock data
# ACTIVE_MATCH = "arsenal_5_1_man_city_2025_02_02"  # real data match 1
# ACTIVE_MATCH = "liverpool_2_0_man_city_2025_02_23"  # real data match 2
```

**Latest results:**
Check `results/{ACTIVE_MATCH}/` folder for the most recent test run files.

## Test Data

The pipeline uses data from `Backend/Mock_Data/{ACTIVE_MATCH}/`:
- `highlight_candidates.json` - Highlight candidate events (D15)
- `dl_handoff.json` - Deep learning handoff events (D17)
- `fusion_summary.json` - Video stitching timestamps (D14)
- `video_analysis_manifest.json` - Video events manifest (D5)
- `audio_analysis_manifest.json` - Audio events manifest (D3)

**Available Matches:**
- `arsenal_vs_city_efl_2026` - Mock data for testing (default)
- `arsenal_5_1_man_city_2025_02_02` - Real match data 1
- `liverpool_2_0_man_city_2025_02_23` - Real match data 2

To switch between demo and production data, edit `config.py`:
```python
DEMO_MODE = True   # Use mock data, skip video stitching
DEMO_MODE = False  # Use real pipeline data, generate videos
```

## What Gets Tested

### Stage 1: Sports Analyst Agent
- ✅ Data loading (mock or real)
- ✅ User preference extraction via LLM query transformation
- ✅ Multi-entity extraction (teams, players, managers from natural language)
- ✅ Event filtering by confidence/importance
- ✅ RAG knowledge base enrichment with extracted search terms
- ✅ Entity lookup with alias resolution (e.g., "Gunners" → Arsenal facts)
- ✅ Transcript context building

### Stage 2: Fan Agent
- ✅ Clip selection (personalized + neutral reels)
- ✅ LLM caption generation via LangChain (PromptTemplate | LLM | StrOutputParser)
- ✅ Evidence tracking for caption sources (D15/D17 fields, RAG facts used)
- ✅ Event deduplication between reels
- ✅ Match recap generation

### Stage 3: Critic Agent
- ✅ Hallucination detection
- ✅ Entity validation against source data
- ✅ Re-captioning with retry logic (preserves evidence through retries)
- ✅ Unsupported mention tracking
- ✅ Preference alignment scoring
- ✅ Evidence summary aggregation (total captions, RAG entities used, fields tracked)

## Expected Output

**Success criteria:**
- All 3 agents complete without errors
- Captions generated for both reels
- Hallucination checks performed
- Evidence tracking displays RAG entities and metadata used
- Results saved to timestamped file

**Typical metrics:**
- Stage 1: ~6-9 events filtered
- Stage 2: 4-5 clips per reel, captions generated
- Stage 3: 0-4 hallucinations detected, 0-2 retries used
