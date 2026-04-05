# RAG Pipeline vs Baseline: Empirical Findings
**Arsenal 5-1 Manchester City** | February 2, 2025

---

## Experiment Design

**Fair Comparison:**
- Same 6 goal events (importance-filtered)
- Same constraint: 10-20 words per caption
- Same user preferences (Arsenal/Man City fan)
- **Only variable:** RAG Multi-Agent vs Single-Prompt

---

## Key Findings

### 1. Instruction Adherence: RAG Wins 100% vs 0%

Both systems prompted: *"Write EXACTLY 10-20 WORDS per caption"*

| Approach | Word Count | Compliance |
|----------|-----------|------------|
| **RAG** | 10-16 words (avg 12.5) | ✅ 100% (12/12) |
| **Baseline** | 4-7 words (avg 5.8) | ❌ 0% (0/12) |

**Example (Ødegaard 2'):**
- RAG: "Ødegaard scores with Havertz' help, Arsenal takes the lead, what a start, brilliant goal!" **(15 words)**
- Baseline: "Ødegaard scores for Arsenal at 2 minutes." **(7 words)**

**Why:** RAG's per-event processing + validation loops enforce constraints better than baseline's batch generation.

---

### 2. Caption Quality: Engaging vs Minimal

**RAG captions:**
- Descriptive language ("what a finish!", "brilliant goal!")
- Player context ("with Havertz' help")
- Emotional tone (fan perspective)
- Full names ("Ethan Nwaneri")

**Baseline captions:**
- Factual only ("[Player] scores for [team]")
- Minimal context
- Generic phrasing

**Example (Havertz 76'):**
- RAG: "Havertz scores a great goal for Arsenal at 76 minutes, what a finish!"
- Baseline: "Havertz scores Arsenal's fourth goal."

---

### 3. Performance: Baseline 150x Faster

| Metric | RAG | Baseline | Winner |
|--------|-----|----------|--------|
| **Time** | 3-5 min | 1.5s | Baseline (150x) |
| **Tokens** | ~6,000 | ~750 | Baseline (8x) |
| **Cost** | ~$0.004 | ~$0.0005 | Baseline (8x) |
| **Complexity** | 3 agents | 1 prompt | Baseline |

---

### 4. Factual Accuracy: Tie

Both 100% accurate on entity names, times, scores. No hallucinations observed in either approach.

**Conclusion:** When using structured event data (D17 JSON), LLMs are naturally accurate. RAG's hallucination checking adds safety but didn't catch errors baseline didn't already avoid.

---

### 5. Evidence Tracking: Missing (Fixed Post-Analysis)

**Issue:** Evidence tracking existed internally but wasn't exported during Arsenal runs.

**Fix:** Now implemented in `pipeline.py` (lines 450-475) for future runs.

**Limitation:** Cannot retroactively generate for Arsenal without invalidating comparison.

**Future output:**
```json
{
  "caption": "...",
  "evidence": {
    "rag_facts": ["Player X"],
    "d15_fields": {"importance": 0.95},
    "d17_fields": {"narrative": "..."},
    "transcript_chunks": ["..."]
  }
}
```

---

## Summary

| Aspect | RAG | Baseline | Winner |
|--------|-----|----------|--------|
| **Instruction Adherence** | 100% | 0% | RAG |
| **Caption Quality** | Engaging | Minimal | RAG |
| **Factual Accuracy** | 100% | 100% | Tie |
| **Speed** | 3-5 min | 1.5s | Baseline |
| **Cost** | 8x more | Baseline | Baseline |
| **Production Ready** | No (too slow) | Yes | Baseline |

---

## Critical Questions

**1. Is the quality improvement worth 150x slowdown?**
- For premium content: Maybe
- For real-time highlights: No
- For scale: No

**2. Is instruction adherence architectural or just per-event processing?**
- Unknown - need to test baseline with per-event prompting
- Could be RAG's validation loops, not retrieval

**3. What is RAG actually retrieving?**
- **Query Transformation:** RAG performs structured extraction of user preferences:
  - Input: `"I am an Arsenal fan"` (raw string)
  - RAG transforms to: `{"preferred_team": "Arsenal", "preferred_players": [], "search_terms": ["Arsenal"]}`
  - Baseline uses raw string directly in prompt (no structured extraction)
  - Enables targeted knowledge base lookups (team facts, player stats, historical context)
- **Evidence Limitation:** No evidence data exported from Arsenal runs to verify what facts were actually retrieved
- Both approaches used same D17 event data (goals, times, players)
- RAG quality difference may come from: (1) query transformation, (2) KB fact enrichment, (3) multi-agent workflow

**Example Query Transformation:**

| User Input | RAG Extraction | Baseline Handling |
|------------|----------------|-------------------|
| "I am an Arsenal fan" | `preferred_team: "Arsenal"`<br>`search_terms: ["Arsenal"]` | Raw string in prompt |
| "I love watching Salah and Martinelli" | `preferred_team: null`<br>`preferred_players: ["Salah", "Martinelli"]`<br>`search_terms: ["Salah", "Martinelli"]` | Raw string in prompt |

RAG's structured extraction enables KB lookups like "Arsenal stadium", "Arsenal manager", "Salah position" - baseline cannot do this.

---

## Recommendations

**For Report:**
1. Highlight instruction adherence as key measurable difference (100% vs 0%)
2. Position RAG as "premium quality" option, not baseline replacement
3. Acknowledge evidence tracking limitation transparently
4. Quantify trade-off: Better quality at 150x cost

**For Future Work:**
1. Test baseline with per-event prompting (isolate architecture vs strategy)
2. Run new match with evidence export to analyze RAG retrieval
3. Analyze query transformation outputs - what search_terms are extracted and used?
4. Profile pipeline to identify bottlenecks
5. Test hybrid: baseline for speed + RAG for top moments

---

**Analysis Date:** April 5, 2026  
**Evidence Available:** No (implemented post-analysis)  
**Methodological Note:** Fair comparison with same events and constraints  
**Comparison:** RAG Multi-Agent Pipeline vs. Baseline Single Prompt
