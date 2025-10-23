import unittest
from unittest.mock import patch

class TestGemini(unittest.TestCase):

    @patch('google.genai.Client')
    def test_client_initialization(self, mock_client):
        # This test ensures that the gemini module can be imported and the client is initialized.
        # The actual client is mocked to avoid making real API calls.
        from llmtitle import gemini
        self.assertIsNotNone(gemini.client)

if __name__ == '__main__':
    unittest.main()