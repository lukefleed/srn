import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import pytest

class TestGemini(unittest.TestCase):

    @patch('llmtitle.credentials.load_api_key')
    @patch('google.genai.Client')
    def test_client_initialization_with_api_key(self, mock_genai_client, mock_load_api_key):
        mock_load_api_key.return_value = "mock_api_key"
        # Reload gemini to ensure client initialization logic runs with the mock
        import importlib
        importlib.reload(sys.modules['llmtitle.gemini'])
        mock_load_api_key.assert_called_once()
        mock_genai_client.assert_called_once_with(api_key="mock_api_key")
        self.assertIsNotNone(sys.modules['llmtitle.gemini'].client)

    @patch('llmtitle.credentials.load_api_key')
    @patch('sys.exit')
    @patch('sys.stderr', new_callable=MagicMock)
    def test_client_initialization_no_api_key(self, mock_stderr, mock_sys_exit, mock_load_api_key):
        mock_load_api_key.return_value = None
        # Reload gemini to ensure client initialization logic runs with the mock
        import importlib
        importlib.reload(sys.modules['llmtitle.gemini'])
        mock_load_api_key.assert_called_once()
        mock_sys_exit.assert_called_once_with(1)
        assert any("Error: Gemini API key not found." in call.args[0] for call in mock_stderr.write.call_args_list)

if __name__ == '__main__':
    unittest.main()