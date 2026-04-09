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
# Source video path for video stitching (set to None to auto-detect from --match-name)
SOURCE_VIDEO_PATH = None  # Auto-detect based on match_name parameter
PROMPTS_PATH = BASE_DIR / "Prompts"
MOCK_DATA_PATH = BASE_DIR / "Mock_Data"
OUTPUT_PATH = BASE_DIR / "Outputs"
KNOWLEDGE_BASE_PATH = BASE_DIR / "knowledge_base.json"

# Mock Data directory
MOCK_DATA_DIR = BASE_DIR / "Mock_Data"

# Current active match — change this to switch matches
ACTIVE_MATCH = "arsenal_5_1_man_city_2025_02_02"  # real data match 1 (6 goals, full evaluation complete)
# ACTIVE_MATCH = "liverpool_2_0_man_city_2024_12_01"  # real data match 2 (2 goals, full evaluation complete)

# Evaluation preferences — DEPRECATED (kept for backward compatibility)
#
# ⚠️ evaluate.py and baseline_single_prompt.py now use DYNAMIC preferences:
#   - evaluate.py --full auto-generates evaluation_config.json with match-specific preferences
#   - baseline_single_prompt.py loads preferences from evaluation_config.json
#   - Preferences are auto-generated from D17 file (team names + goal scorers)
#
# This hardcoded Liverpool list is no longer used but kept to avoid breaking imports.
#
EVAL_PREFERENCES = [
    "I am a Liverpool fan and I love watching Liverpool play",
    "I support Manchester City and I follow Manchester City closely",
    "I am a neutral viewer and I want to see all the goals from this match",
    "I love watching C. Gakpo play for Liverpool, he is my favourite player",
    "I love watching Mohamed Salah play for Liverpool, he is my favourite player",
]

# Configurable output directory for pipeline JSONs
PIPELINE_OUTPUT_DIR = Path(os.getenv("PIPELINE_OUTPUT_DIR", str(BASE_DIR / "Outputs")))

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # Options: "groq" or "gemini"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# API Keys for external services
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
API_SPORTS_KEY = os.getenv("API_SPORTS_KEY")

# Model names
GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.5-flash"  # Back to flash - pro returned empty captions

# Processing thresholds
IMPORTANCE_THRESHOLD = 0.5
MAX_HIGHLIGHTS = 6  # 6 clips × 10s = ~1 minute reel
MIN_CONFIDENCE = 0.5
MAX_RETRIES = 2
ALIGNMENT_THRESHOLD = 0.35  # Cosine similarity threshold for preference alignment
DISAGREEMENT_IMPORTANCE_THRESHOLD = 0.8  # Clips below this threshold get challenged by Critic

# Importance scores by event type for clip selection
EVENT_IMPORTANCE = {
    'goal': 0.95,
    'penalty_goal': 0.95,
    'penalty_awarded': 0.85,
    'var_review': 0.75,
    'stoppage_review': 0.75,
    'card': 0.60,
    'foul': 0.55,
    'substitution': 0.30,  # low — only include if nothing better
}

# Demo mode (set to True to use mock data for testing)
DEMO_MODE = False

# Subtitle typing effect configuration
ENABLE_TYPING_EFFECT = True  # Enable character-by-character reveal
TYPING_SPEED_CPS = 50  # Characters per second (higher = faster typing)

# Prompt template paths
CAPTION_PERSONALISED_PROMPT = PROMPTS_PATH / "caption_personalised.txt"
CAPTION_NEUTRAL_PROMPT = PROMPTS_PATH / "caption_neutral.txt"
HALLUCINATION_CHECK_PROMPT = PROMPTS_PATH / "hallucination_check.txt"

# File paths — auto-resolved from ACTIVE_MATCH
# Approach B — Fully Autonomous (API-Football + Gemini Vision)
D15_FILE_PATH = MOCK_DATA_DIR / ACTIVE_MATCH / "approach_b_highlight_candidates.json"
D17_FILE_PATH = MOCK_DATA_DIR / ACTIVE_MATCH / "approach_b_dl_handoff.json"

# Legacy paths for backward compatibility
D15_MOCK_DATA = D15_FILE_PATH
D17_MOCK_DATA = D17_FILE_PATH
