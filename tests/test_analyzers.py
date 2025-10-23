
import unittest
from unittest.mock import patch, MagicMock
import pathlib
import tempfile
from llmtitle.analyzers import DocumentAnalyzer, MediaAnalyzer

class TestAnalyzers(unittest.TestCase):

    @patch('llmtitle.analyzers.genai.Client')
    def test_document_analyzer(self, mock_client):
        # Mock the Gemini API response
        mock_response = MagicMock()
        mock_response.text = '{"type": "book", "title": "new_book_title", "author": "test_author"}'
        mock_response.usage_metadata.total_token_count = 100
        mock_client.return_value.models.generate_content.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = pathlib.Path(tmpdir) / "original.pdf"
            filepath.touch()

            analyzer = DocumentAnalyzer()
            response_text, token_count = analyzer.analyze(filepath, "test_model")

            self.assertEqual(token_count, 100)
            self.assertIn("new_book_title", response_text)

    @patch('llmtitle.analyzers.TinyTag.get')
    @patch('llmtitle.analyzers.genai.Client')
    def test_media_analyzer(self, mock_client, mock_tinytag):
        # Mock TinyTag
        mock_tag = MagicMock()
        mock_tag.as_dict.return_value = {'title': 'My Movie', 'year': '2023'}
        mock_tinytag.return_value = mock_tag

        # Mock the Gemini API response
        mock_response = MagicMock()
        mock_response.text = '{"title": "my_movie", "year": "2023"}'
        mock_response.usage_metadata.total_token_count = 50
        mock_client.return_value.models.generate_content.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = pathlib.Path(tmpdir) / "my_movie.mkv"
            filepath.touch()

            analyzer = MediaAnalyzer()
            response_text, token_count = analyzer.analyze(filepath, "test_model")

            self.assertEqual(token_count, 50)
            self.assertIn("my_movie", response_text)

if __name__ == '__main__':
    unittest.main()
