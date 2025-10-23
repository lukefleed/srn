import sys
from google import genai

# --- Gemini Client Setup ---
try:
    client = genai.Client()
except Exception as e:
    print(f"Error: Could not initialize Gemini client. Make sure the GOOGLE_API_KEY environment variable is set.", file=sys.stderr)
    print(f"Error detail: {e}", file=sys.stderr)
    sys.exit(1)

# --- Model Configuration ---
ALLOWED_MODELS = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"]
DEFAULT_MODEL = ALLOWED_MODELS[0]