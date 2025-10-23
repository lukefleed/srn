
import sys
import pathlib
from pypdf import PdfReader

from google import genai
from google.genai import types

from .utils import get_file_mime_type

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
# --- End Model Configuration ---

def build_gemini_prompt(context: str = None):
    """Builds the detailed JSON-mode prompt for Gemini."""
    
    context_prompt = ""
    if context:
        context_prompt = f"""
        An important piece of context has been provided by the user, which you should use to guide your response:
        ---
        {context}
        ---
        """

    return f"""
    Analyze the content of this file (the first 2-3 pages are likely sufficient).
    It is often an academic document (lecture notes, exam, book, or scientific paper),
    but it could be any general document.

    {context_prompt}

    Identify the document type and relevant information to rename it.

    IMPORTANT: Generate all string values (like title, subject, author) in the *same language* as the source document.

    The renaming rules are:
    1.  **Notes**: subject, year, author.
    2.  **Exam**: subject, date.
    3.  **Book**: title, author.
    4.  **Paper**: title (short), first_author, year.
    5.  **Other**: A general descriptive title.

    Respond EXCLUSIVELY with a single JSON object. NEVER add text before or after the JSON (not even ```json).

    The JSON format must be:
    {{
      "type": "..." (possible values: "notes", "exam", "book", "paper", "other"),
      "subject": "..." (e.g., "mathematical_analysis_1", or null if not found),
      "year": "..." (only year, e.g., "2024", or null if not found),
      "author": "..." (for books/notes, or null),
      "first_author": "..." (ONLY for papers, e.g., "afroozeh", or null),
      "date": "..." (ONLY for exams, e.g., "2024_01_15", or null),
      "title": "..." (for books, papers, or 'other'.
                     If 'paper', MUST be 3-5 keywords.
                     If 'book', the full title.
                     If 'other', a general descriptive title based on content, including dates or names if relevant.)
    }}

    Normalize all extracted values: all lowercase and use '_' (underscore) instead of spaces.
    If a piece of information required by the rules is not present, its value must be null.
    """

def get_new_filename_from_gemini(filepath: pathlib.Path, model_name: str, disable_thinking: bool = False, context: str = None, max_pages: int = None) -> tuple[str, int]:
    """
    Loads the file, queries the Gemini API, and returns the raw text response and token count.
    Returns (str: response_text, int: total_token_count) on success, or (None, 0) on failure.
    """
    if not filepath.exists():
        print(f"Error: File '{filepath}' does not exist.", file=sys.stderr)
        return None, 0

    mime_type = get_file_mime_type(filepath)

    if mime_type == 'application/pdf' and max_pages is not None and max_pages > 0:
        try:
            reader = PdfReader(filepath)
            text_content = ""
            for i, page in enumerate(reader.pages):
                if i >= max_pages:
                    break
                text_content += page.extract_text() or ""
            
            file_part = types.Part.from_text(text=text_content)

        except Exception as e:
            print(f"Error reading PDF file '{filepath}': {e}", file=sys.stderr)
            return None, 0
    else:
        try:
            file_data = filepath.read_bytes()
            file_part = types.Part.from_bytes(
                data=file_data,
                mime_type=mime_type
            )
        except Exception as e:
            print(f"Error reading file '{filepath}': {e}", file=sys.stderr)
            return None, 0

    prompt = build_gemini_prompt(context)

    gen_config = None
    if disable_thinking:
        gen_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[file_part, prompt],
            config=gen_config
        )
        return response.text, response.usage_metadata.total_token_count
    except Exception as e:
        print(f"Error during Gemini API call for '{filepath.name}' (model: {model_name}): {e}", file=sys.stderr)
        return None, 0
