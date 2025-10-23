import json
import os
import pathlib
import stat
import sys
from dotenv import load_dotenv, set_key

CREDENTIALS_DIR_NAME = ".srn"
ENV_FILE_NAME = ".env"
API_KEY_VAR_NAME = "GEMINI_API_KEY"

def _get_credentials_dir() -> pathlib.Path:
    """Returns the path to the directory where credentials are stored."""
    home_dir = pathlib.Path.home()
    credentials_dir = home_dir / CREDENTIALS_DIR_NAME
    credentials_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    return credentials_dir

def _get_env_file_path() -> pathlib.Path:
    """Returns the path to the .env file."""
    return _get_credentials_dir() / ENV_FILE_NAME

def save_api_key(api_key: str):
    """Saves the API key to a secure .env file."""
    env_file_path = _get_env_file_path()
    try:
        # Ensure the directory exists with correct permissions
        _get_credentials_dir()

        # Use python-dotenv's set_key to update or add the API key
        set_key(str(env_file_path), API_KEY_VAR_NAME, api_key)

        # Set restrictive permissions on the .env file
        os.chmod(env_file_path, stat.S_IRUSR | stat.S_IWUSR) # rw-------
    except IOError as e:
        print(f"Error saving API key: {e}", file=sys.stderr)
        sys.exit(1)

def load_api_key() -> str | None:
    """Loads the API key from the secure .env file or environment variables."""
    env_file_path = _get_env_file_path()
    if env_file_path.exists():
        load_dotenv(dotenv_path=env_file_path)
    
    # Always check environment variables, as load_dotenv populates them
    return os.getenv(API_KEY_VAR_NAME)

def prompt_for_api_key():
    """Prompts the user for their API key and saves it."""
    print("Please insert your Gemini API Key:")
    api_key = input().strip()
    if api_key:
        save_api_key(api_key)
        print("API Key saved successfully.")
    else:
        print("No API Key entered. Aborting.", file=sys.stderr)
        sys.exit(1)
