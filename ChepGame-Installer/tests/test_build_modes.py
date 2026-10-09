"""Check build-mode contract without a PS4 toolchain."""
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class BuildModesTests(unittest.TestCase):
    def make_var(self, mode, var):
        result = subprocess.run(
            ['make', '-s', '--eval', 'probe:;@echo $(' + var + ')', 'DIAGNOSTIC_ONLY=' + mode, 'probe'],
            cwd=ROOT, check=True, capture_output=True, text=True)
        return result.stdout.strip()

    def test_default_install_manifest_requires_jbc(self):
        files = self.make_var('0', 'PACKAGE_FILES')
        self.assertIn('sce_module/libjbc.sprx', files)

    def test_diagnostic_manifest_excludes_jbc_even_if_asset_present(self):
        files = self.make_var('1', 'PACKAGE_FILES')
        self.assertNotIn('libjbc.sprx', files)
        self.assertIn('sce_module/libSceFios2.prx', files)

    def test_install_mode_fails_early_without_jbc(self):
        if (ROOT/'assets/libjbc.sprx').exists():
            self.skipTest('local module present')
        result = subprocess.run(['make', '-s', 'DIAGNOSTIC_ONLY=0', 'check-jbc'],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('libjbc.sprx missing', result.stdout + result.stderr)

    def test_diagnostic_mode_does_not_require_asset(self):
        subprocess.run(['make','-s','DIAGNOSTIC_ONLY=1','check-jbc'],
                       cwd=ROOT, check=True, capture_output=True, text=True)

if __name__ == '__main__':
    unittest.main()
