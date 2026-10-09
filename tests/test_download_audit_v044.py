"""v0.4.4 real-generation and failure path checks."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class DownloadAuditV044Tests(unittest.TestCase):
    def test_source_pipeline_no_errno_only_abort(self):
        from tests.fixture_prepare import PrepareTests
        from prepare_native import prepare
        test = PrepareTests('test_output')
        test.setUp()
        try:
            prepare(test.source,ROOT,'http://192.168.1.6:8099/orbis/catalog.json')
            code=(test.source/'src/main.cpp').read_text()
            for needle in ('chepgame_download_fs.hpp','ensure_writable_dir(',
                           'FALLBACK_DIR','DIR_BOTH_FAILED','SHA_MISMATCH',
                           'PKG đã có trong /data/pkg – không tải lại',
                           'chepgame_using_fallback',
                           'Tải hoàn tất – PKG sẵn sàng tại /data/pkg'):
                if needle == 'SHA_MISMATCH': needle = 'EXISTING_SHA_MISMATCH'
                self.assertIn(needle,code,needle)
            self.assertNotIn('if(errno!=ENOENT)',code)
            self.assertNotIn('Không thể kiểm tra thư mục /data/pkg',code)
            self.assertIn('VERSION     := 0.45',(test.source/'Makefile').read_text())
            self.assertTrue((test.source/'src/chepgame_download_fs.hpp').exists())
            # The legacy BGFT helpers are still referenced by the native UI.
            # Linking without these libs caused an unresolved-symbol build.
            make=(test.source/'Makefile').read_text()
            self.assertIn('-lSceAppInstUtil -lSceBgft ',make)
            workflow=(ROOT/'.github/workflows/build-ps4.yml').read_text()
            self.assertIn('tests.test_download_stable_v043',workflow)
            self.assertNotIn('tests.test_download_stable_v044',workflow)
            self.assertIn('ChepGameStore-PS4-v0.4.5.pkg',workflow)
        finally:
            test.tearDown()
    def test_writable_dir_host_cpp(self):
        result=subprocess.run(['g++','-std=c++11','-Wall','-Wextra','-Werror','-I',str(ROOT),
            str(ROOT/'tests/test_download_fs_v044.cpp'),'-o','/tmp/chepgame-fs-v044'],
            capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        result=subprocess.run(['/tmp/chepgame-fs-v044'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
