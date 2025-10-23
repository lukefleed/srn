import os
import sys
import stat
import json
import pytest
from unittest.mock import patch, MagicMock

from llmtitle import credentials

# Mock the home directory for testing
@pytest.fixture
def mock_home_dir(tmp_path):
    original_home = os.environ.get("HOME")
    os.environ["HOME"] = str(tmp_path)
    yield tmp_path
    if original_home:
        os.environ["HOME"] = original_home
    else:
        del os.environ["HOME"]

@pytest.fixture(autouse=True)
def unset_gemini_api_key_env():
    original_gemini_api_key = os.environ.pop(credentials.API_KEY_VAR_NAME, None)
    yield
    if original_gemini_api_key is not None:
        os.environ[credentials.API_KEY_VAR_NAME] = original_gemini_api_key

@pytest.fixture
def mock_credentials_dir(mock_home_dir):
    return mock_home_dir / credentials.CREDENTIALS_DIR_NAME

@pytest.fixture
def mock_env_file(mock_credentials_dir):
    return mock_credentials_dir / credentials.ENV_FILE_NAME

def test_get_credentials_dir(mock_home_dir, mock_credentials_dir):
    path = credentials._get_credentials_dir()
    assert path == mock_credentials_dir
    assert path.is_dir()
    assert (path.stat().st_mode & 0o777) == 0o700 # Check permissions

def test_get_env_file_path(mock_home_dir, mock_env_file):
    path = credentials._get_env_file_path()
    assert path == mock_env_file

def test_save_api_key(mock_env_file, mock_credentials_dir):
    api_key = "test_api_key_123"
    credentials.save_api_key(api_key)

    assert mock_env_file.is_file()
    assert (mock_env_file.stat().st_mode & 0o777) == 0o600 # Check permissions

    with open(mock_env_file, "r") as f:
        content = f.read()
        assert f"{credentials.API_KEY_VAR_NAME}='{api_key}'\n" == content

def test_load_api_key_from_file(mock_env_file):
    api_key = "test_api_key_456"
    # Ensure the credentials directory exists
    credentials._get_credentials_dir()
    with open(mock_env_file, "w") as f:
        f.write(f"{credentials.API_KEY_VAR_NAME}={api_key}")
    os.chmod(mock_env_file, 0o600)

    loaded_key = credentials.load_api_key()
    assert loaded_key == api_key

def test_load_api_key_file_not_exists(mock_env_file):
    # Temporarily unset the environment variable for this test
    original_gemini_api_key = os.environ.pop(credentials.API_KEY_VAR_NAME, None)

    # Ensure file does not exist
    if mock_env_file.exists():
        mock_env_file.unlink()
    
    loaded_key = credentials.load_api_key()
    assert loaded_key is None

    # Restore the environment variable
    if original_gemini_api_key is not None:
        os.environ[credentials.API_KEY_VAR_NAME] = original_gemini_api_key

def test_load_api_key_from_env_var(mock_home_dir):
    # Ensure no file exists
    env_file = credentials._get_env_file_path()
    if env_file.exists():
        env_file.unlink()

    os.environ[credentials.API_KEY_VAR_NAME] = "env_api_key_789"
    loaded_key = credentials.load_api_key()
    assert loaded_key == "env_api_key_789"
    del os.environ[credentials.API_KEY_VAR_NAME]

def test_prompt_for_api_key_success(mock_home_dir):
    with patch("builtins.input", return_value="prompted_key_123"), \
         patch("sys.stdout", new=MagicMock()) as mock_stdout_print, \
         patch("sys.exit") as mock_exit:
        credentials.prompt_for_api_key()
        mock_exit.assert_not_called()
        assert any("API Key saved successfully." in call.args[0] for call in mock_stdout_print.write.call_args_list)
        loaded_key = credentials.load_api_key()
        assert loaded_key == "prompted_key_123"

def test_prompt_for_api_key_empty_input(mock_home_dir):
    with patch("builtins.input", return_value=""), \
         patch("sys.stderr", new=MagicMock()) as mock_stderr_print, \
         patch("sys.exit") as mock_exit:
        credentials.prompt_for_api_key()
        mock_exit.assert_called_once_with(1)
        assert any("No API Key entered. Aborting." in call.args[0] for call in mock_stderr_print.write.call_args_list)
