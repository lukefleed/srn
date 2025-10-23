import unittest
import pathlib
import tempfile
from llmtitle.utils import ThreadSafeCounter, get_file_mime_type, discover_files

class TestUtils(unittest.TestCase):

    def test_thread_safe_counter(self):
        counter = ThreadSafeCounter()
        self.assertEqual(counter.value, 0)
        counter.increment()
        self.assertEqual(counter.value, 1)
        counter.increment(5)
        self.assertEqual(counter.value, 6)

    def test_get_file_mime_type(self):
        self.assertEqual(get_file_mime_type(pathlib.Path("test.pdf")), "application/pdf")
        self.assertEqual(get_file_mime_type(pathlib.Path("test.txt")), "text/plain")
        self.assertEqual(get_file_mime_type(pathlib.Path("test.tex")), "text/plain")
        self.assertEqual(get_file_mime_type(pathlib.Path("test.md")), "text/plain")
        self.assertEqual(get_file_mime_type(pathlib.Path("test.unknown")), "application/octet-stream")

    def test_discover_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = pathlib.Path(tmpdir)
            (dir_path / "file1.pdf").touch()
            (dir_path / "file2.txt").touch()
            (dir_path / "sub").mkdir()
            (dir_path / "sub" / "file3.pdf").touch()

            # Test with single extension
            files = discover_files([str(dir_path)], "pdf")
            self.assertEqual(len(files), 2)
            self.assertIn(pathlib.Path(dir_path / "file1.pdf").resolve(), files)
            self.assertIn(pathlib.Path(dir_path / "sub" / "file3.pdf").resolve(), files)

            # Test with multiple extensions
            files = discover_files([str(dir_path)], "pdf,txt")
            self.assertEqual(len(files), 3)

            # Test with a single file
            files = discover_files([str(dir_path / "file1.pdf")], "pdf")
            self.assertEqual(len(files), 1)

if __name__ == '__main__':
    unittest.main()