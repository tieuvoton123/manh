import contextlib
import importlib.util
import io
import pathlib
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fetch_installer_jbc", ROOT / "fetch_jbc.py")
fetch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch)
TEST_SELF = fetch.SELF_MAGIC + b"\0" * 7000


class JbcFetchTests(unittest.TestCase):
    def test_upstream_pinned_commit_and_expected_binary_identity(self):
        self.assertEqual(len(fetch.PINNED_COMMIT), 40)
        self.assertEqual(fetch.EXPECTED_BLOB_SHA, "281946bfa3803426da3a48e78f647349400986f9")
        self.assertEqual(fetch.EXPECTED_SIZE, 9952)
        self.assertEqual(fetch.SELF_MAGIC, bytes.fromhex("4f153d1d"))

    def test_diagnostic_does_not_download_or_create_module(self):
        with tempfile.TemporaryDirectory() as d:
            dest = pathlib.Path(d) / "libjbc.sprx"
            with mock.patch.object(fetch, "download_pinned", side_effect=AssertionError("unexpected download")):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(fetch.install(dest, diagnostic_only=True), "diagnostic")
            self.assertFalse(dest.exists())

    def test_diagnostic_ignores_existing_local_self(self):
        with tempfile.TemporaryDirectory() as d:
            dest = pathlib.Path(d) / "libjbc.sprx"
            dest.write_bytes(b"broken existing file")
            with mock.patch.object(fetch, "download_pinned", side_effect=AssertionError("must not download")):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(fetch.install(dest, diagnostic_only=True), "diagnostic")
            self.assertEqual(dest.read_bytes(), b"broken existing file")

    def test_local_self_is_kept_unchanged_and_network_not_used(self):
        with tempfile.TemporaryDirectory() as d:
            dest = pathlib.Path(d) / "libjbc.sprx"
            dest.write_bytes(TEST_SELF)
            with mock.patch.object(fetch, "download_pinned", side_effect=AssertionError("unexpected download")):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(fetch.install(dest), "local")
            self.assertEqual(dest.read_bytes(), TEST_SELF)

    def test_invalid_existing_file_is_rejected_not_replaced(self):
        with tempfile.TemporaryDirectory() as d:
            dest = pathlib.Path(d) / "libjbc.sprx"
            dest.write_bytes(b"test stub")
            with mock.patch.object(fetch, "download_pinned", side_effect=AssertionError("unexpected download")):
                with self.assertRaisesRegex(ValueError, "Not a PS4 SELF"):
                    fetch.install(dest)
            self.assertEqual(dest.read_bytes(), b"test stub")

    def test_successful_fetch_verifies_blob_then_atomically_saves(self):
        with tempfile.TemporaryDirectory() as d:
            dest = pathlib.Path(d) / "assets" / "libjbc.sprx"
            with mock.patch.object(fetch, "EXPECTED_SIZE", len(TEST_SELF)), \
                 mock.patch.object(fetch, "EXPECTED_BLOB_SHA", fetch.git_blob_sha(TEST_SELF)), \
                 mock.patch.object(fetch, "download_pinned", return_value=TEST_SELF):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(fetch.install(dest), "downloaded")
            self.assertEqual(dest.read_bytes(), TEST_SELF)
            self.assertEqual(len(list(dest.parent.iterdir())), 1)

    def test_failed_upstream_check_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as d:
            dest = pathlib.Path(d) / "assets" / "libjbc.sprx"
            with mock.patch.object(fetch, "download_pinned", return_value=TEST_SELF):
                with self.assertRaisesRegex(ValueError, "size mismatch"):
                    fetch.install(dest)
            self.assertFalse(dest.exists())

    def test_workflow_uses_helper_before_compiling(self):
        workflow = (ROOT.parent / ".github/workflows/build-chepgame-installer.yml").read_text()
        self.assertIn('python3 fetch_jbc.py', workflow)
        self.assertIn('python3 fetch_jbc.py --diagnostic-only', workflow)
        self.assertIn('-e DIAGNOSTIC_ONLY="$DIAGNOSTIC_ONLY"', workflow)
        self.assertIn("grep -q 'libjbc.sprx' pkg.gp4", workflow)
        self.assertIn('ChepGame-Installer-PS4-v0.3.3.pkg', workflow)
        self.assertLess(workflow.index('python3 fetch_jbc.py'), workflow.index('Compile PS4 ELF'))


if __name__ == '__main__':
    unittest.main()
