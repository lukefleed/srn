from abc import ABC, abstractmethod
import pathlib
import sys
import json
from pypdf import PdfReader
from tinytag import TinyTag
from google import genai
from google.genai import types
from . import gemini
from .utils import get_file_mime_type

class Analyzer(ABC):
    @abstractmethod
    def analyze(self, filepath: pathlib.Path, **kwargs) -> tuple[dict, int]:
        pass

class DocumentAnalyzer(Analyzer):
    @staticmethod
    def parse_gemini_response(response_text: str) -> dict:
        """
        Extracts and parses the JSON from Gemini's response.
        Returns (dict: data) on success, or (None) on failure.
        """
        if not response_text:
            print(f"Error: Gemini's response was empty.", file=sys.stderr)
            return None

        try:
            clean_text = response_text.strip().replace("```json", "").replace("```", "").strip()
            if not clean_text:
                 print(f"Error: Gemini's response was empty after cleaning.", file=sys.stderr)
                 return None
            data = json.loads(clean_text)
            return data
        except json.JSONDecodeError:
            print(f"Error: Gemini's response was not valid JSON.", file=sys.stderr)
            print(f"Response received: {response_text}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Unknown error while parsing response: {e}", file=sys.stderr)
            return None

    def _build_document_prompt(self, filepath: pathlib.Path, context: str = None) -> str:
        context_prompt = ""
        if context:
            context_prompt = f"""
            An important piece of context has been provided by the user, which you should use to guide your response:
            ---
            {context}
            ---
            """

        parent_dir = filepath.parent
        grandparent_dir = parent_dir.parent
        last_two_dirs = f"{grandparent_dir.name}/{parent_dir.name}"

        return f"""
        Analyze the content of this file. The original filename is '{filepath.name}'. The file is located in the path '{last_two_dirs}'.
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

    def analyze(self, filepath: pathlib.Path, model_name: str, disable_thinking: bool = False, context: str = None, max_pages: int = None) -> tuple[dict, int]:
        if not filepath.exists():
            print(f"Error: File '{filepath}' does not exist.", file=sys.stderr)
            return None, 0

        mime_type = get_file_mime_type(filepath)

        try:
            file_data = filepath.read_bytes()
            file_part = types.Part.from_bytes(
                data=file_data,
                mime_type=mime_type
            )
        except Exception as e:
            print(f"Error reading file '{filepath}': {e}", file=sys.stderr)
            return None, 0

        prompt = self._build_document_prompt(filepath, context)

        # If max_pages is specified, add it to the prompt instructions
        if max_pages is not None and max_pages > 0:
            prompt += f"\nAnalyze only the first {max_pages} pages of the document."

        gen_config = None
        if disable_thinking:
            gen_config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            )

        try:
            client = gemini.get_gemini_client()
            response = client.models.generate_content(
                model=model_name,
                contents=[file_part, prompt],
                config=gen_config
            )
            return response.text, response.usage_metadata.total_token_count
        except Exception as e:
            print(f"Error during Gemini API call for '{filepath.name}' (model: {model_name}): {e}", file=sys.stderr)
            return None, 0

class MediaAnalyzer(Analyzer):
    @staticmethod
    def parse_gemini_response(response_text: str) -> dict:
        """
        Extracts and parses the JSON from Gemini's response.
        Returns (dict: data) on success, or (None) on failure.
        """
        if not response_text:
            print(f"Error: Gemini's response was empty.", file=sys.stderr)
            return None

        try:
            clean_text = response_text.strip().replace("```json", "").replace("```", "").strip()
            if not clean_text:
                 print(f"Error: Gemini's response was empty after cleaning.", file=sys.stderr)
                 return None
            data = json.loads(clean_text)
            return data
        except json.JSONDecodeError:
            print(f"Error: Gemini's response was not valid JSON.", file=sys.stderr)
            print(f"Response received: {response_text}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Unknown error while parsing response: {e}", file=sys.stderr)
            return None
            
    def _build_media_prompt(self, filepath: pathlib.Path, filename: str, metadata: dict, context: str = None) -> str:
        context_prompt = ""
        if context:
            context_prompt = f"""
            An important piece of context has been provided by the user, which you should use to guide your response:
            ---
            {context}
            ---
            """

        parent_dir = filepath.parent
        grandparent_dir = parent_dir.parent
        last_two_dirs = f"{grandparent_dir.name}/{parent_dir.name}"

        return f"""
        You are a file organization expert. Your task is to suggest a clean, descriptive filename for a media file.
        It is important to consider the current filename: {filename}. The file is located in the path '{last_two_dirs}'.
        
        Analyze the following information:
        - Current Filename: {filename}
        - Metadata: {metadata}
        {context_prompt}

        Follow these rules:
        1.  **Movies/TV Shows**: Use the format `{{title}}_{{year}}`.
        2.  **Images/Audio**: If a date is available, use `{{yyyy-mm-dd}}_{{title}}`. If not, use `{{title}}`.
        3.  If the original filename contains important information not in the metadata, try to preserve it.
        4.  If there is not enough information to create a meaningful name, just clean up the existing filename (lowercase, replace spaces with underscores).

        Respond EXCLUSIVELY with a single JSON object. The JSON format must be:
        {{
          "title": "...",
          "year": "..." (or null),
          "creation_date": "..." (in yyyy-mm-dd format, or null)
        }}
        """

    def analyze(self, filepath: pathlib.Path, model_name: str, disable_thinking: bool = False, context: str = None, **kwargs) -> tuple[dict, int]:
        try:
            tag = TinyTag.get(filepath)
            metadata = tag.as_dict()
        except Exception as e:
            print(f"Error reading metadata from '{filepath}': {e}", file=sys.stderr)
            metadata = {}

        prompt = self._build_media_prompt(filepath, filepath.name, metadata, context)

        gen_config = None
        if disable_thinking:
            gen_config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            )

        try:
            client = gemini.get_gemini_client()
            response = client.models.generate_content(
                model=model_name,
                contents=[prompt],
                config=gen_config
            )
            return response.text, response.usage_metadata.total_token_count
        except Exception as e:
            print(f"Error during Gemini API call for '{filepath.name}' (model: {model_name}): {e}", file=sys.stderr)
            return None, 0