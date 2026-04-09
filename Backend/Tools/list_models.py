from google import genai
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment from Backend/.env
backend_dir = Path(__file__).parent.parent
load_dotenv(backend_dir / ".env")

api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("ERROR: GEMINI_API_KEY not found in .env")
    exit(1)

client = genai.Client(api_key=api_key)

print("Available Gemini models:\n")
for m in client.models.list():
    print(f"  {m.name}")
