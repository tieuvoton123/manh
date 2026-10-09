"""Regression tests: 0.4.5 UI/Makefile must pass the CI guard.

These tests run against a generated source fixture and do not claim that an
OpenOrbis PKG was built or that the app was run on a console.
"""
from pathlib import Path
import subprocess
import sys
import unittest
from tests.fixture_prepare import PrepareTests
from prepare_native import prepare

ROOT = Path(__file__).resolve().parents[1]


class UiBuildGuardTests(unittest.TestCase):
    def setUp(self):
        self.fixture = PrepareTests('test_output')
        self.fixture.setUp()
        prepare(self.fixture.source, ROOT, 'http://192.168.1.6:8099/orbis/catalog.json')
        # The prepare fixture intentionally omits the upstream HTTP client.
        # Provide its three expected guard tokens only in this synthetic test;
        # the real CI checks the generated upstream implementation independently.
        http = self.fixture.source / 'src/http_client.cpp'
        http.write_text(http.read_text(encoding='utf-8') +
                        '\n// fixture: sceHttpGetResponseContentLength(handles.req' +
                        ' completed==expected_size network_read_error\n',
                        encoding='utf-8')

    def tearDown(self):
        self.fixture.tearDown()

    def check(self):
        return subprocess.run([sys.executable, str(ROOT / 'kiem_tra_giao_dien.py'),
                               str(self.fixture.source)],
                              capture_output=True, text=True)

    def test_v045_generated_source_passes(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_stale_ui_version_fails(self):
        path = self.fixture.source / 'src/main.cpp'
        content = path.read_text(encoding='utf-8')
        self.assertIn('BY SUPER MANH  v0.45', content)
        path.write_text(content.replace('BY SUPER MANH  v0.45',
                                        'BY SUPER MANH  v0.44', 1), encoding='utf-8')
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('UI thiếu phiên bản v0.45', result.stderr)

    def test_stale_makefile_version_fails(self):
        path = self.fixture.source / 'Makefile'
        content = path.read_text(encoding='utf-8')
        self.assertIn('VERSION     := 0.45', content)
        path.write_text(content.replace('VERSION     := 0.45',
                                        'VERSION     := 0.44', 1), encoding='utf-8')
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Makefile VERSION phải là 0.45', result.stderr)


if __name__ == '__main__':
    unittest.main()
