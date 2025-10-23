import sys
from google import genai
from . import credentials

# --- Model Configuration ---
ALLOWED_MODELS = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"]
DEFAULT_MODEL = ALLOWED_MODELS[0]

_gemini_client = None

def get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        try:
            api_key = credentials.load_api_key()
            if not api_key:
                print("Error: Gemini API key not found. Please set the GEMINI_API_KEY environment variable or use 'srn --api-key' to save it.", file=sys.stderr)
                sys.exit(1)
            _gemini_client = genai.Client(api_key=api_key)
        except Exception as e:
            print(f"Error: Could not initialize Gemini client. Make sure the GEMINI_API_KEY environment variable is set or saved using 'srn --api-key'.", file=sys.stderr)
            print(f"Error detail: {e}", file=sys.stderr)
            sys.exit(1)
    return _gemini_client