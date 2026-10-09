"""Offline tests for the pinned, atomic stb_truetype downloader."""
from contextlib import redirect_stdout
from io import BytesIO, StringIO
import hashlib
import pathlib
import runpy
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "fetch_stb_header.py"


class StbFetchHotfixTests(unittest.TestCase):
    def make_fixture(self, directory, blob_contents=b"// mocked upstream stb header\n"):
        path = pathlib.Path(directory) / "fetch_stb_header.py"
        sha = hashlib.sha1(b"blob " + str(len(blob_contents)).encode() + b"\0" + blob_contents).hexdigest()
        text = SCRIPT.read_text(encoding="utf-8").replace(
            'BLOB = "90a5c2e2b3fe563c98585294ca7a949876aec94c"',
            f'BLOB = "{sha}"',
        )
        path.write_text(text, encoding="utf-8")
        return path, pathlib.Path(directory) / "stb_truetype.h"

    def run_script(self, path, mocked_data):
        with patch("urllib.request.urlopen", return_value=BytesIO(mocked_data)) as download:
            with redirect_stdout(StringIO()):
                runpy.run_path(str(path), run_name="__main__")
        return download

    def test_replaces_existing_syntax_only_stub(self):
        with tempfile.TemporaryDirectory() as td:
            body = b"// authentic pinned header (mock)\n"
            script, header = self.make_fixture(td, body)
            header.write_bytes(b"#pragma once\n// Developer syntax-only stub\n")
            download = self.run_script(script, body)
            download.assert_called_once()
            self.assertEqual(header.read_bytes(), body)

    def test_verified_cached_header_skips_download(self):
        with tempfile.TemporaryDirectory() as td:
            body = b"// approved content\n"
            script, header = self.make_fixture(td, body)
            header.write_bytes(body)
            with patch("urllib.request.urlopen", side_effect=AssertionError("unexpected fetch")):
                with redirect_stdout(StringIO()):
                    runpy.run_path(str(script), run_name="__main__")
            self.assertEqual(header.read_bytes(), body)

    def test_hash_mismatch_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as td:
            script, header = self.make_fixture(td, b"expected content")
            header.write_bytes(b"existing stub")
            with self.assertRaisesRegex(SystemExit, "Mismatch stb_truetype.h"):
                self.run_script(script, b"tampered content")
            self.assertEqual(header.read_bytes(), b"existing stub")
            self.assertEqual(list(pathlib.Path(td).glob('.stb-*.tmp')), [])

    def test_download_failure_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as td:
            script, header = self.make_fixture(td)
            header.write_bytes(b"existing stub")
            with patch("urllib.request.urlopen", side_effect=OSError("offline")):
                with self.assertRaisesRegex(SystemExit, "Cannot download pinned"):
                    with redirect_stdout(StringIO()):
                        runpy.run_path(str(script), run_name="__main__")
            self.assertEqual(header.read_bytes(), b"existing stub")

    def test_original_commit_and_digest_unchanged(self):
        content = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('COMMIT = "2c980bb59875b0d32144a71867fbdebb2f77cd20"', content)
        self.assertIn('BLOB = "90a5c2e2b3fe563c98585294ca7a949876aec94c"', content)
        self.assertIn('tmp_path.replace(path)', content)


if __name__ == "__main__":
    unittest.main()
