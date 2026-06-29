import os
from pathlib import Path
import tempfile
import unittest

import server


class ServerTests(unittest.TestCase):
    def test_clean_filename_removes_paths_and_unsafe_chars(self):
        self.assertEqual(server.clean_filename("../a b.png"), "a-b.png")
        self.assertEqual(server.clean_filename("..."), "file")

    def test_raw_upload_requires_filename(self):
        with self.assertRaisesRegex(ValueError, "X-Filename"):
            server.parse_upload({"Content-Type": "application/octet-stream"}, b"abc")

    def test_save_upload_writes_unique_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_dir = server.UPLOAD_DIR
            server.UPLOAD_DIR = Path(os.path.abspath(tmp))
            try:
                stored, path = server.save_upload("a.txt", b"hello")
                self.assertTrue(stored.endswith("-a.txt"))
                self.assertEqual(path.read_bytes(), b"hello")
            finally:
                server.UPLOAD_DIR = old_dir


if __name__ == "__main__":
    unittest.main()
