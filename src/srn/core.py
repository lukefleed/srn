
import json
import re
import sys
import pathlib

from .analyzers import DocumentAnalyzer, MediaAnalyzer
from .utils import ThreadSafeCounter, get_file_mime_type

def format_new_name(info: dict, template: str = None):
    """
    Builds the new filename from the structured info and sanitizes it.
    Returns (str: safe_name) or (None).
    """
    if template:
        # Find all placeholders like {key}
        keys = re.findall(r'{([^}]+)}', template)
        parts = [info.get(key) for key in keys]
        final_name = "_".join(p for p in parts if p)
    else:
        tipo = info.get("type")
        parts = []

        if tipo == "notes":
            parts = [info.get("subject"), info.get("year"), info.get("author")]
        elif tipo == "exam":
            parts = [info.get("subject"), info.get("date")]
        elif tipo == "book":
            parts = [info.get("title"), info.get("author")]
        elif tipo == "paper":
            parts = [info.get("title"), info.get("first_author"), info.get("year")]
        elif tipo == "other":
            parts = [info.get("title"), info.get("subject")]
        else:
            parts = [info.get("title"), info.get("subject")]

        final_name = "_".join(p for p in parts if p)

    if not final_name:
        return None

    safe_name = final_name.replace(" ", "_")
    safe_name = re.sub(r'[^\w\-_.]', '', safe_name)
    safe_name = re.sub(r'[_.-]+', '_', safe_name)
    safe_name = safe_name.strip('_')

    return safe_name

def get_unique_path(path: pathlib.Path) -> pathlib.Path:
    """If a path exists, appends a number to it until it is unique."""
    if not path.exists():
        return path
    
    parent = path.parent
    stem = path.stem
    suffix = path.suffix
    
    counter = 1
    while True:
        new_stem = f"{stem}_{counter}"
        new_path = parent / f"{new_stem}{suffix}"
        if not new_path.exists():
            return new_path
        counter += 1

def process_and_rename_file(filepath: pathlib.Path, model_name: str, disable_thinking: bool, dry_run: bool = False, on_conflict: str = "skip", template: str = None, context: str = None, max_pages: int = None, token_counter: ThreadSafeCounter = None) -> tuple:
    """
    Worker function to process a single file.
    This function performs all steps: API call, parsing, formatting, and renaming.
    Returns a tuple: (original_path, new_path, status_message)
    """
    # 1. Choose analyzer based on file type
    mime_type = get_file_mime_type(filepath)
    if mime_type.startswith('video') or mime_type.startswith('audio') or mime_type.startswith('image'):
        analyzer = MediaAnalyzer()
    else:
        analyzer = DocumentAnalyzer()

    # 2. Analyze the file
    raw_response, token_count = analyzer.analyze(
        filepath,
        model_name=model_name,
        disable_thinking=disable_thinking,
        context=context,
        max_pages=max_pages
    )
    if token_counter and token_count > 0:
        token_counter.increment(token_count)

    if not raw_response:
        return (filepath, None, "Gemini API call failed")

    # 3. Parse the JSON response
    info = analyzer.parse_gemini_response(raw_response)
    if not info:
        return (filepath, None, "Failed to parse Gemini JSON response")

    # 4. Format the new name
    new_base_name = format_new_name(info, template)
    if not new_base_name:
        return (filepath, None, f"Could not generate a valid name from info: {info}")

    # 5. Handle conflicts
    file_extension = filepath.suffix
    new_filename = f"{new_base_name}{file_extension}"
    new_filepath = filepath.with_name(new_filename)

    if filepath == new_filepath:
        return (filepath, new_filepath, "skipped")

    if new_filepath.exists():
        if on_conflict == "skip":
            return (filepath, new_filepath, "conflict_skipped")
        elif on_conflict == "rename":
            new_filepath = get_unique_path(new_filepath)
        # For "overwrite", we just proceed

    if dry_run:
        return (filepath, new_filepath, "dry_run_success")

    try:
        filepath.rename(new_filepath)
        return (filepath, new_filepath, "success")
    except OSError as e:
        return (filepath, new_filepath, f"OS error renaming: {e}")
    except Exception as e:
        return (filepath, new_filepath, f"Unknown error renaming: {e}")
