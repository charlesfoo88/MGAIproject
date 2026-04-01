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
PROMPTS_PATH = BASE_DIR / "Prompts"
MOCK_DATA_PATH = BASE_DIR / "Mock_Data"
OUTPUT_PATH = BASE_DIR / "Outputs"
KNOWLEDGE_BASE_PATH = BASE_DIR / "knowledge_base.json"

# Configurable output directory for pipeline JSONs
PIPELINE_OUTPUT_DIR = Path(os.getenv("PIPELINE_OUTPUT_DIR", str(BASE_DIR / "Outputs")))

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")  # Options: "groq" or "gemini"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

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

# Mock data paths
D15_MOCK_DATA = MOCK_DATA_PATH / "highlight_candidates_mock.json"
D17_MOCK_DATA = MOCK_DATA_PATH / "dl_handoff_mock.json"

# Real pipeline JSON file paths
D15_FILE_PATH = PIPELINE_OUTPUT_DIR / "d15_highlight_candidates.json"
D17_FILE_PATH = PIPELINE_OUTPUT_DIR / "d17_dl_handoff.json"
