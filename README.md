# MGAI — AI-Powered Sports Highlight Generator

Automated sports match highlight reel generator using multi-agent AI pipeline with hallucination detection and video stitching.

## 🎯 Overview

This system generates **three personalized highlight reels** from sports matches:
- **Team 1 Fan**: Enthusiastic perspective for first team
- **Team 2 Fan**: Enthusiastic perspective for second team  
- **Neutral**: Balanced broadcaster-style coverage

**Key Features:**
- 🤖 3-stage AI agent pipeline (Analyst → Fan → Critic)
- 🧠 LLM-based query transformation with RAG-enhanced entity verification
- 📝 Complete LLM-generated captions with hallucination detection
- 🎬 Automated video extraction and stitching with typing effect subtitles
- ⚡ Configurable LLM providers (Groq Llama-3.3-70b or Gemini 2.5 Flash)
- 📊 Comprehensive evaluation framework (cross-modal, verifier, disagreement, self-consistency)

## 📚 Documentation

For detailed setup, usage, and technical documentation:

- **[Backend/README.md](Backend/README.md)** - Complete backend documentation (installation, pipeline, API, evaluation, baselines)
- **[Frontend/README.md](Frontend/README.md)** - Frontend setup and UI documentation

## 🚀 Quick Start

```bash
# Backend setup
cd Backend
pip install -r requirements.txt

# Run pipeline
python pipeline.py --match-name arsenal_5_1_man_city_2025_02_02 --all-perspectives

# Frontend setup
cd Frontend
npm install
npm run dev
```

**Prerequisites:** Python 3.8+, FFmpeg, API keys (Gemini, optional: Groq)

See [Backend/README.md](Backend/README.md) for complete installation and usage instructions.
