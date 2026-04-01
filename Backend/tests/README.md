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
- Save timestamped results to `tests/results/test_result_YYYYMMDD_HHMMSS.txt`

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

All test outputs are saved to `results/` folder with timestamps for easy tracking and debugging.

**Latest results:**
Check `results/` folder for the most recent test run files.

## Test Data

The pipeline uses mock data from `Backend/Mock_Data/`:
- `highlight_candidates_mock.json` - Sample highlight events
- `dl_handoff_mock.json` - Sample deep learning handoff events

To switch between demo and production data, edit `config.py`:
```python
DEMO_MODE = True   # Use mock data
DEMO_MODE = False  # Use real pipeline data from Outputs/
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
- ✅ Event deduplication between reels
- ✅ Match recap generation

### Stage 3: Critic Agent
- ✅ Hallucination detection
- ✅ Entity validation against source data
- ✅ Re-captioning with retry logic
- ✅ Unsupported mention tracking
- ✅ Preference alignment scoring

## Expected Output

**Success criteria:**
- All 3 agents complete without errors
- Captions generated for both reels
- Hallucination checks performed
- Results saved to timestamped file

**Typical metrics:**
- Stage 1: ~6-9 events filtered
- Stage 2: 4-5 clips per reel, captions generated
- Stage 3: 0-4 hallucinations detected, 0-2 retries used
