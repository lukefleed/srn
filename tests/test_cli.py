import pytest
import sys
from unittest.mock import patch, MagicMock

from llmtitle import cli
from llmtitle import credentials

@pytest.fixture
def mock_sys_exit():
    with patch("sys.exit") as mock_exit:
        yield mock_exit

@pytest.fixture
def mock_prompt_for_api_key():
    with patch.object(credentials, "prompt_for_api_key") as mock_prompt:
        yield mock_prompt

def test_api_key_flag_prompts_and_exits(mock_sys_exit, mock_prompt_for_api_key):
    # Simulate command line arguments: llm-title --api-key
    with patch.object(sys, "argv", ["llm-title", "--api-key"]):
        cli.main()
        mock_prompt_for_api_key.assert_called_once()
        mock_sys_exit.assert_called_once_with(0)
