
import unittest
from unittest.mock import patch, MagicMock
import pathlib
import tempfile
from pypdf import PdfWriter
from llmtitle.gemini import build_gemini_prompt, get_new_filename_from_gemini

class TestGemini(unittest.TestCase):

    def test_build_gemini_prompt_with_context(self):
        context = "These are all exam papers from the University of Bologna."
        prompt = build_gemini_prompt(context)
        self.assertIn(context, prompt)

    def test_build_gemini_prompt_without_context(self):
        prompt = build_gemini_prompt()
        self.assertNotIn("An important piece of context has been provided by the user", prompt)

    @patch('google.genai.client.Client.models')
    def test_get_new_filename_from_gemini_max_pages(self, mock_models):
        # Create a dummy PDF with two pages
        writer = PdfWriter()
        writer.add_blank_page(width=8.5 * 72, height=11 * 72) # Letter size
        writer.add_blank_page(width=8.5 * 72, height=11 * 72)
        
        # This is a hack to get some text into the PDF for testing
        # In a real scenario, you'd use a library like reportlab to draw text
        # For this test, we'll mock the text extraction
        page1_text = "This is page 1."
        page2_text = "This is page 2."

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            filepath = pathlib.Path(tmp.name)
            writer.write(tmp.name)

        # Mock the PdfReader
        mock_reader = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = page1_text
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = page2_text
        mock_reader.pages = [mock_page1, mock_page2]

        with patch('llmtitle.gemini.PdfReader', return_value=mock_reader):
            get_new_filename_from_gemini(filepath, "test_model", max_pages=1)

        # Assertion
        mock_models.generate_content.assert_called_once()
        call_args, call_kwargs = mock_models.generate_content.call_args
        sent_content = call_kwargs['contents'][0].text
        self.assertIn(page1_text, sent_content)
        self.assertNotIn(page2_text, sent_content)

        # Clean up
        filepath.unlink()
