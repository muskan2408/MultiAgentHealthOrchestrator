import os
from dotenv import load_dotenv

load_dotenv()

#Gemini API KEY
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

# LiquidAI API key
# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# if not OPENROUTER_API_KEY:
#     raise ValueError("OPENROUTER_API_KEY not found in .env file")

# # Set it in the environment for the API client
# os.environ["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY

MODEL_NAME = "gemini/gemini-2.5-flash-lite"
#MODEL_NAME = "openrouter/liquid/lfm-2.5-1.2b-thinking:free"
MAX_TOKENS = 1024
TEMPERATURE = 0.3
