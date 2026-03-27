import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

MODEL_NAME = "gemini/gemini-2.5-flash"
MAX_TOKENS = 2048
TEMPERATURE = 0.3
