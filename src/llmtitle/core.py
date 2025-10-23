
import json
import re
import sys
import pathlib

from .gemini import get_new_filename_from_gemini

def parse_gemini_response(response_text: str):
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

def format_new_name(info: dict):
    """
    Builds the new filename from the structured info and sanitizes it.
    Returns (str: safe_name) or (None).
    """
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
    safe_name = re.sub(r'[^\w\-_]', '', safe_name)
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

def process_and_rename_file(filepath: pathlib.Path, model_name: str, disable_thinking: bool, dry_run: bool = False, on_conflict: str = "skip") -> tuple:
    """
    Worker function to process a single file.
    This function performs all steps: API call, parsing, formatting, and renaming.
    Returns a tuple: (original_path, new_path, status_message)
    """
    # 1. Call Gemini
    raw_response = get_new_filename_from_gemini(
        filepath,
        model_name,
        disable_thinking
    )
    if not raw_response:
        return (filepath, None, "Gemini API call failed")

    # 2. Parse the JSON response
    info = parse_gemini_response(raw_response)
    if not info:
        return (filepath, None, "Failed to parse Gemini JSON response")

    # 3. Format the new name
    new_base_name = format_new_name(info)
    if not new_base_name:
        return (filepath, None, f"Could not generate a valid name from info: {info}")

    # 4. Handle conflicts
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
