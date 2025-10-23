
import unittest
from unittest.mock import patch, MagicMock
import pathlib
import tempfile
from llmtitle.core import format_new_name, get_unique_path, process_and_rename_file
from llmtitle.utils import ThreadSafeCounter

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

    def test_format_new_name_with_template(self):
        info = {
            "title": "My_Awesome_Paper",
            "first_author": "Doe",
            "year": "2024",
            "journal": "Nature"
        }
        template = "{first_author}_{year}_{title}"
        expected = "Doe_2024_My_Awesome_Paper"
        self.assertEqual(format_new_name(info, template), expected)

    def test_format_new_name_with_template_missing_keys(self):
        info = {
            "title": "My_Awesome_Paper",
            "year": "2024",
        }
        template = "{first_author}_{year}_{title}"
        expected = "2024_My_Awesome_Paper"
        self.assertEqual(format_new_name(info, template), expected)

    def test_get_unique_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = pathlib.Path(tmpdir)
            file1 = dir_path / "file.txt"
            file1.touch()
            file2 = dir_path / "file_1.txt"
            file2.touch()

            new_path = get_unique_path(file1)
            self.assertEqual(new_path.name, "file_2.txt")

    @patch('llmtitle.core.DocumentAnalyzer.analyze')
    def test_conflict_skip(self, mock_analyze):
        mock_analyze.return_value = ('{"type": "book", "title": "conflict_name", "author": "test"}', 100)
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = pathlib.Path(tmpdir)
            original_file = dir_path / "original.pdf"
            original_file.touch()
            conflict_file = dir_path / "conflict_name_test.pdf"
            conflict_file.touch()

            _, _, status = process_and_rename_file(original_file, "model", False, on_conflict="skip", template="{title}_{author}")

            self.assertEqual(status, "conflict_skipped")
            self.assertTrue(original_file.exists())
            self.assertTrue(conflict_file.exists())

    @patch('llmtitle.core.DocumentAnalyzer.analyze')
    def test_conflict_overwrite(self, mock_analyze):
        mock_analyze.return_value = ('{"type": "book", "title": "conflict_name", "author": "test"}', 100)
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = pathlib.Path(tmpdir)
            original_file = dir_path / "original.pdf"
            original_file.write_text("original content")
            conflict_file = dir_path / "conflict_name_test.pdf"
            conflict_file.write_text("conflict content")

            _, new_filepath, status = process_and_rename_file(original_file, "model", False, on_conflict="overwrite", template="{title}_{author}")

            self.assertEqual(status, "success")
            self.assertFalse(original_file.exists())
            self.assertTrue(new_filepath.exists())
            self.assertEqual(new_filepath.read_text(), "original content")

    @patch('llmtitle.core.DocumentAnalyzer.analyze')
    def test_conflict_rename(self, mock_analyze):
        mock_analyze.return_value = ('{"type": "book", "title": "conflict_name", "author": "test"}', 100)
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = pathlib.Path(tmpdir)
            original_file = dir_path / "original.pdf"
            original_file.touch()
            conflict_file = dir_path / "conflict_name_test.pdf"
            conflict_file.touch()

            _, new_filepath, status = process_and_rename_file(original_file, "model", False, on_conflict="rename", template="{title}_{author}")

            self.assertEqual(status, "success")
            self.assertFalse(original_file.exists())
            self.assertTrue(new_filepath.exists())
            self.assertEqual(new_filepath.name, "conflict_name_test_1.pdf")

if __name__ == '__main__':
    unittest.main()
