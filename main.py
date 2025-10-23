#!/usr/bin/env python3

"""
llm-title: AI-Powered File Renamer

This script uses Google Gemini to intelligently rename files based on their content.
It is optimized for academic documents like papers, books, and notes but can be
applied to any text-based file.

USAGE:
    llm-title [OPTIONS] <FILE_OR_DIRECTORY>...

EXAMPLES:
    1. Rename a single file:
       llm-title /path/to/document.pdf

    2. Process multiple files in parallel:
       llm-title -r file1.pdf "My Report.docx" notes.txt

    3. Recursively scan a directory for PDF and Markdown files:
       llm-title -r --ext pdf,md /path/to/my/documents/

    4. Scan multiple directories with a specific number of jobs:
       llm-title -r -j 8 /path/to/notes/ /path/to/papers/

OPTIONS:
    -m, --model MODEL
        Specify the Gemini model to use.
        Default: gemini-2.5-flash-lite
        Choices: gemini-2.5-flash-lite, gemini-2.5-flash, gemini-2.5-pro

    -r, --recursive
        Enable batch processing for multiple files or directories.
        This flag is required when providing more than one path or a directory.

    -j, --jobs NUM
        Number of parallel jobs for batch processing.
        Defaults to the system's CPU count.

    --ext EXTENSIONS
        Comma-separated list of file extensions to process in batch mode.
        Default: pdf

    --no-thinking
        Disable the 'thinking' animation during Gemini API calls. This may speed up processing.
"""

import os
import sys
import json
import re
import pathlib
import argparse
import mimetypes
import concurrent.futures
import os
from functools import partial
from google import genai
from google.genai import types

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
DEFAULT_EXTENSIONS = "pdf"
# --- End Model Configuration ---

def get_file_mime_type(filepath: pathlib.Path):
    """Guesses the file's MIME type from its path."""
    mime_type, _ = mimetypes.guess_type(filepath)
    if mime_type is None:
        if filepath.suffix in ['.tex', '.txt', '.md']:
            return 'text/plain'
        return 'application/octet-stream'
    return mime_type

def build_gemini_prompt():
    """Builds the detailed JSON-mode prompt for Gemini."""
    return """
    Analyze the content of this file (the first 2-3 pages are likely sufficient).
    It is often an academic document (lecture notes, exam, book, or scientific paper),
    but it could be any general document.

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
    {
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
    }

    Normalize all extracted values: all lowercase and use '_' (underscore) instead of spaces.
    If a piece of information required by the rules is not present, its value must be null.
    """

def get_new_filename_from_gemini(filepath: pathlib.Path, model_name: str, disable_thinking: bool = False):
    """
    Loads the file, queries the Gemini API, and returns the raw text response.
    Returns (str: response_text) on success, or (None) on failure.
    """
    if not filepath.exists():
        print(f"Error: File '{filepath}' does not exist.", file=sys.stderr)
        return None

    try:
        file_data = filepath.read_bytes()
        mime_type = get_file_mime_type(filepath)

        file_part = types.Part.from_bytes(
            data=file_data,
            mime_type=mime_type
        )
    except Exception as e:
        print(f"Error reading file '{filepath}': {e}", file=sys.stderr)
        return None

    prompt = build_gemini_prompt()

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
        return response.text
    except Exception as e:
        print(f"Error during Gemini API call for '{filepath.name}' (model: {model_name}): {e}", file=sys.stderr)
        return None

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

def discover_files(input_paths: list[str], extensions_str: str) -> list[pathlib.Path]:
    """
    Scans all input paths for files matching the allowed extensions.
    - If a path is a file, it's checked.
    - If a path is a directory, it's scanned recursively.
    Returns a list of unique pathlib.Path objects.
    """
    files_to_process = set()
    allowed_extensions = {f".{ext.strip().lower()}" for ext in extensions_str.split(',')}

    for path_str in input_paths:
        path = pathlib.Path(path_str)
        if not path.exists():
            print(f"Warning: Path does not exist, skipping: {path_str}", file=sys.stderr)
            continue

        if path.is_file():
            if path.suffix.lower() in allowed_extensions:
                files_to_process.add(path.resolve())
        elif path.is_dir():
            for file_path in path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in allowed_extensions:
                    files_to_process.add(file_path.resolve())

    return list(files_to_process)

def process_and_rename_file(filepath: pathlib.Path, model_name: str, disable_thinking: bool) -> tuple:
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

    # 4. Perform the rename
    file_extension = filepath.suffix
    new_filename = f"{new_base_name}{file_extension}"
    new_filepath = filepath.with_name(new_filename)

    if filepath == new_filepath:
        return (filepath, new_filepath, "skipped")

    try:
        filepath.rename(new_filepath)
        return (filepath, new_filepath, "success")
    except OSError as e:
        return (filepath, new_filepath, f"OS error renaming: {e}")
    except Exception as e:
        return (filepath, new_filepath, f"Unknown error renaming: {e}")

def setup_arg_parser():
    """Configures and returns the argparse.ArgumentParser."""
    parser = argparse.ArgumentParser(
        description="Automatically rename files based on their content using Gemini.",
        usage="%(prog)s [options] FILE_OR_DIR [FILE_OR_DIR ...]",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__ # Use the module docstring as the epilog
    )

    parser.add_argument(
        "input_paths",
        type=str,
        nargs='+',
        help="One or more paths to files or directories to process."
    )

    parser.add_argument(
        "-m", "--model",
        type=str,
        default=DEFAULT_MODEL,
        choices=ALLOWED_MODELS,
        metavar="MODEL",
        help=f"Specify the Gemini model. (Default: {DEFAULT_MODEL})"
    )

    parser.add_argument(
        "--no-thinking",
        action="store_true",
        default=False,
        help="Disable the 'thinking' feature for the model."
    )

    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        default=False,
        help="Enable recursive batch processing for directories or multiple files."
    )

    parser.add_argument(
        "-j", "--jobs",
        type=int,
        default=None,
        metavar="NUM",
        help="Number of parallel jobs (threads). Only used with -r. (Default: CPU count)"
    )

    parser.add_argument(
        "--ext",
        type=str,
        default=DEFAULT_EXTENSIONS,
        metavar="EXTENSIONS",
        help=f"Comma-separated file extensions to process (e.g., pdf,tex). Only used with -r. (Default: \"{DEFAULT_EXTENSIONS}\")"
    )

    return parser

class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'

def main():
    parser = setup_arg_parser()
    args = parser.parse_args()

    # --- Argument Validation ---
    if not args.recursive:
        if len(args.input_paths) > 1:
            parser.error("Multiple paths provided without the -r flag. Use -r to process a batch.")

        path = pathlib.Path(args.input_paths[0])
        if path.is_dir():
            parser.error("Cannot process a directory without the -r flag. Use -r to scan recursively.")
        if not path.exists():
            parser.error(f"File not found: {path}")
        if not path.is_file():
            parser.error(f"Input path is not a file: {path}")

        # Non-recursive options check
        if args.jobs is not None:
            print("Warning: -j/--jobs flag has no effect without -r.", file=sys.stderr)
        if args.ext != DEFAULT_EXTENSIONS:
            parser.error("--ext can only be used with the -r flag.")

        files_to_process = [path]
        num_workers = 1

    else:
        # Recursive / Batch mode
        files_to_process = discover_files(args.input_paths, args.ext)
        if not files_to_process:
            print("No files found matching the criteria.")
            sys.exit(0)

        num_workers = args.jobs if args.jobs is not None and args.jobs > 0 else os.cpu_count()
        if num_workers is None:
            num_workers = 4 # Fallback if os.cpu_count() fails

        # Use the smaller of desired workers or number of files
        # Do not spawn more threads than there are files to process.
        desired_workers = args.jobs if args.jobs is not None and args.jobs > 0 else os.cpu_count()
        if desired_workers is None:
            desired_workers = 4 # Fallback if os.cpu_count() fails

        num_workers = min(desired_workers, len(files_to_process))

    # --- Setup Worker Function ---
    worker_func = partial(
        process_and_rename_file,
        model_name=args.model,
        disable_thinking=args.no_thinking
    )

    # --- Execution ---
    print(f"Found {len(files_to_process)} file(s). Processing with {num_workers} worker(s)...")

    success_count = 0
    skipped_count = 0
    error_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        try:
            results = list(executor.map(worker_func, files_to_process))
        except KeyboardInterrupt:
            print(f"\n{Colors.RED}Caught Interrupt. Shutting down workers...{Colors.ENDC}", file=sys.stderr)
            executor.shutdown(wait=False, cancel_futures=True)
            sys.exit(1)

    print(f"\n{Colors.BOLD}--- Processing Complete ---{Colors.ENDC}")
    for original, new, status in results:
        if status == "success":
            print(f"{Colors.GREEN}[OK] Renamed:{Colors.ENDC}\n     {original.name}\n  -> {new.name}")
            success_count += 1
        elif status == "skipped":
            print(f"{Colors.YELLOW}[SKIP] Name already correct: {original.name}{Colors.ENDC}")
            skipped_count += 1
        else:
            print(f"{Colors.RED}[FAIL] {original.name}\n     Error: {status}{Colors.ENDC}", file=sys.stderr)
            error_count += 1

    print(f"\n{Colors.BOLD}--- Summary ---{Colors.ENDC}")
    print(f"{Colors.GREEN}Successful: {success_count}{Colors.ENDC}")
    print(f"{Colors.YELLOW}Skipped:    {skipped_count}{Colors.ENDC}")
    if error_count > 0:
        print(f"{Colors.RED}Failed:     {error_count}{Colors.ENDC}")
    else:
        print(f"Failed:     {error_count}")

    if error_count > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
