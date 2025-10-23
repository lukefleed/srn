
import mimetypes
import pathlib
import sys

class TerminalColors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'

def get_file_mime_type(filepath: pathlib.Path):
    """Guesses the file's MIME type from its path."""
    mime_type, _ = mimetypes.guess_type(filepath)
    if mime_type is None:
        if filepath.suffix in ['.tex', '.txt', '.md']:
            return 'text/plain'
        return 'application/octet-stream'
    return mime_type

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
