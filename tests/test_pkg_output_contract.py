"""Offline validator regression tests; fake data is never called a usable PKG."""
import importlib.util
import pathlib
import struct
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('verify_ps4_pkg', ROOT / 'verify_ps4_pkg.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ArtifactVerificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        d = pathlib.Path(self.tmp.name)
        self.pkg = d / 'build.pkg'
        self.gp4 = d / 'pkg.gp4'
        self.sfo = d / 'param.sfo'
        self.tid = 'CHEP00002'
        self.cid = 'IV0000-CHEP00002_00-CHEPINSTALLER001'
        header = bytearray(131072)
        header[:4] = b'\x7fCNT'
        struct.pack_into('>I', header, 0xc, 6)
        header[0x40:0x64] = self.cid.encode()
        self.pkg.write_bytes(header)
        self.gp4.write_text('<psproject><volume><package>'+self.cid+'</package></volume>\n'
                            'eboot.bin sce_sys/param.sfo sce_sys/icon0.png '
                            'sce_sys/about/right.sprx sce_module/libc.prx '
                            'sce_module/libSceFios2.prx sce_module/libjbc.sprx</psproject>')
        self.sfo.write_bytes(b'\x00PSF\x00' + self.tid.encode() + b'\0' + self.cid.encode())

    def run_check(self, mode='required'):
        return module.verify(self.pkg, self.gp4, self.sfo, self.tid, self.cid, mode)

    def test_mocked_header_accepted_for_structural_checks_only(self):
        self.assertEqual(self.run_check()['title_id'], self.tid)

    def test_rejects_false_pkg(self):
        self.pkg.write_bytes(b'not a pkg' * 10000)
        with self.assertRaisesRegex(ValueError, 'magic'):
            self.run_check()

    def test_rejects_wrong_content_id(self):
        header = bytearray(self.pkg.read_bytes())
        header[0x40:0x64] = b'X' * 36
        self.pkg.write_bytes(header)
        with self.assertRaisesRegex(ValueError, 'Content ID'):
            self.run_check()

    def test_diagnostic_rejects_jbc(self):
        with self.assertRaisesRegex(ValueError, 'DIAGNOSTIC'):
            self.run_check('forbidden')

    def test_install_rejects_missing_jbc(self):
        self.gp4.write_text(self.gp4.read_text().replace('sce_module/libjbc.sprx', ''))
        with self.assertRaisesRegex(ValueError, 'libjbc'):
            self.run_check('required')

    def test_rejects_empty_sfo(self):
        self.sfo.write_bytes(b'')
        with self.assertRaisesRegex(ValueError, 'empty'):
            self.run_check()


if __name__ == '__main__':
    unittest.main()
