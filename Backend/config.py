import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from Backend/.env (if python-dotenv is installed)
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv(BASE_DIR / ".env")
SOURCE_VIDEOS_PATH = BASE_DIR / "Source_Videos"
# Source video path for video stitching
SOURCE_VIDEO_PATH = BASE_DIR / "Source_Videos" / "test_clip.mp4"
PROMPTS_PATH = BASE_DIR / "Prompts"
MOCK_DATA_PATH = BASE_DIR / "Mock_Data"
OUTPUT_PATH = BASE_DIR / "Outputs"
KNOWLEDGE_BASE_PATH = BASE_DIR / "knowledge_base.json"

# Mock Data directory
MOCK_DATA_DIR = BASE_DIR / "Mock_Data"

# Current active match — change this to switch matches
ACTIVE_MATCH = "arsenal_5_1_man_city_2025_02_02"
# ACTIVE_MATCH = "arsenal_vs_city_efl_2026"  # mock data
# ACTIVE_MATCH = "liverpool_2_0_man_city_2025_02_23"  # real data match 2

# Configurable output directory for pipeline JSONs
PIPELINE_OUTPUT_DIR = Path(os.getenv("PIPELINE_OUTPUT_DIR", str(BASE_DIR / "Outputs")))

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")  # Options: "groq" or "gemini"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# API Keys for external services
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
API_SPORTS_KEY = os.getenv("API_SPORTS_KEY")

# Model names
GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-1.5-flash"

# Processing thresholds
IMPORTANCE_THRESHOLD = 0.5
MAX_HIGHLIGHTS = 5
MIN_CONFIDENCE = 0.5
MAX_RETRIES = 2
ALIGNMENT_THRESHOLD = 0.35  # Cosine similarity threshold for preference alignment

# Demo mode (set to True to use mock data for testing)
DEMO_MODE = True

# Prompt template paths
CAPTION_PERSONALISED_PROMPT = PROMPTS_PATH / "caption_personalised.txt"
CAPTION_NEUTRAL_PROMPT = PROMPTS_PATH / "caption_neutral.txt"
HALLUCINATION_CHECK_PROMPT = PROMPTS_PATH / "hallucination_check.txt"

# File paths — auto-resolved from ACTIVE_MATCH
# Approach B — Fully Autonomous (API-Football + Gemini Vision)
D15_FILE_PATH = MOCK_DATA_DIR / ACTIVE_MATCH / "approach_b_highlight_candidates.json"
D17_FILE_PATH = MOCK_DATA_DIR / ACTIVE_MATCH / "approach_b_dl_handoff.json"
D14_FILE_PATH = MOCK_DATA_DIR / ACTIVE_MATCH / "fusion_summary.json"

# Mock data (previous approach — kept for reference)
# D15_FILE_PATH = MOCK_DATA_DIR / "arsenal_vs_city_efl_2026" / "highlight_candidates.json"
# D17_FILE_PATH = MOCK_DATA_DIR / "arsenal_vs_city_efl_2026" / "dl_handoff.json"

# Legacy paths for backward compatibility
D15_MOCK_DATA = D15_FILE_PATH
D17_MOCK_DATA = D17_FILE_PATH
