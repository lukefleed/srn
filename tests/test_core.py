
import unittest
from unittest.mock import patch, MagicMock
import pathlib
import tempfile
from llmtitle.core import format_new_name, process_and_rename_file

class TestCore(unittest.TestCase):

    def test_format_new_name_notes(self):
        info = {
            "type": "notes",
            "subject": "math_analysis_1",
            "year": "2024",
            "author": "prof_rossi"
        }
        expected = "math_analysis_1_2024_prof_rossi"
        self.assertEqual(format_new_name(info), expected)

    def test_format_new_name_exam(self):
        info = {
            "type": "exam",
            "subject": "data_structures",
            "date": "2024_07_22"
        }
        expected = "data_structures_2024_07_22"
        self.assertEqual(format_new_name(info), expected)

    def test_format_new_name_book(self):
        info = {
            "type": "book",
            "title": "the_hitchhikers_guide_to_the_galaxy",
            "author": "douglas_adams"
        }
        expected = "the_hitchhikers_guide_to_the_galaxy_douglas_adams"
        self.assertEqual(format_new_name(info), expected)

    def test_format_new_name_paper(self):
        info = {
            "type": "paper",
            "title": "attention_is_all_you_need",
            "first_author": "vaswani",
            "year": "2017"
        }
        expected = "attention_is_all_you_need_vaswani_2017"
        self.assertEqual(format_new_name(info), expected)

    def test_format_new_name_other(self):
        info = {
            "type": "other",
            "title": "my_vacation_photos",
            "subject": None
        }
        expected = "my_vacation_photos"
        self.assertEqual(format_new_name(info), expected)

    def test_format_new_name_with_nulls(self):
        info = {
            "type": "notes",
            "subject": "history",
            "year": None,
            "author": "dr_jones"
        }
        expected = "history_dr_jones"
        self.assertEqual(format_new_name(info), expected)

    def test_format_new_name_sanitization(self):
        info = {
            "type": "other",
            "title": "  A Title With--Weird__Chars!!  ",
            "subject": "stuff"
        }
        expected = "A_Title_With_Weird_Chars_stuff"
        self.assertEqual(format_new_name(info), expected)

    @patch('llmtitle.core.get_new_filename_from_gemini')
    def test_process_and_rename_file_dry_run(self, mock_gemini):
        # Mock the Gemini response
        mock_gemini.return_value = '{"type": "book", "title": "new_book_title", "author": "test_author"}'

        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            filepath = pathlib.Path(tmp.name)

        original_name = filepath.name

        # Call the function with dry_run=True
        _, new_filepath, status = process_and_rename_file(
            filepath,
            model_name="test_model",
            disable_thinking=True,
            dry_run=True
        )

        # Assertions
        self.assertEqual(status, "dry_run_success")
        self.assertEqual(new_filepath.name, "new_book_title_test_author.pdf")
        self.assertTrue(filepath.exists()) # File should still exist with original name
        self.assertEqual(filepath.name, original_name)

        # Clean up the temporary file
        filepath.unlink()

    @patch('llmtitle.core.get_new_filename_from_gemini')
    def test_conflict_skip(self, mock_gemini):
        mock_gemini.return_value = '{"type": "book", "title": "conflict_name", "author": "test"}'
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = pathlib.Path(tmpdir)
            original_file = dir_path / "original.pdf"
            original_file.touch()
            conflict_file = dir_path / "conflict_name_test.pdf"
            conflict_file.touch()

            _, _, status = process_and_rename_file(original_file, "model", False, False, "skip")

            self.assertEqual(status, "conflict_skipped")
            self.assertTrue(original_file.exists())
            self.assertTrue(conflict_file.exists())

    @patch('llmtitle.core.get_new_filename_from_gemini')
    def test_conflict_overwrite(self, mock_gemini):
        mock_gemini.return_value = '{"type": "book", "title": "conflict_name", "author": "test"}'
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = pathlib.Path(tmpdir)
            original_file = dir_path / "original.pdf"
            original_file.write_text("original content")
            conflict_file = dir_path / "conflict_name_test.pdf"
            conflict_file.write_text("conflict content")

            _, new_filepath, status = process_and_rename_file(original_file, "model", False, False, "overwrite")

            self.assertEqual(status, "success")
            self.assertFalse(original_file.exists())
            self.assertTrue(new_filepath.exists())
            self.assertEqual(new_filepath.read_text(), "original content")

    @patch('llmtitle.core.get_new_filename_from_gemini')
    def test_conflict_rename(self, mock_gemini):
        mock_gemini.return_value = '{"type": "book", "title": "conflict_name", "author": "test"}'
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = pathlib.Path(tmpdir)
            original_file = dir_path / "original.pdf"
            original_file.touch()
            conflict_file = dir_path / "conflict_name_test.pdf"
            conflict_file.touch()

            _, new_filepath, status = process_and_rename_file(original_file, "model", False, False, "rename")

            self.assertEqual(status, "success")
            self.assertFalse(original_file.exists())
            self.assertTrue(new_filepath.exists())
            self.assertEqual(new_filepath.name, "conflict_name_test_1.pdf")

if __name__ == '__main__':
    unittest.main()
