import pathlib
import subprocess
import unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
class NativeSourceTests(unittest.TestCase):
    def test_all_cpp11_compile_against_api(self):
        for name in ('installer.cpp','pkg_scan.cpp','font.cpp','main.cpp','task_guard.cpp'):
            with self.subTest(name=name):
                subprocess.run(['g++','-std=c++11','-Wall','-Wextra','-Werror','-fsyntax-only',
                                '-I'+str(ROOT/'tests/stubs'),'-I'+str(ROOT/'src'),
                                str(ROOT/'src'/name)],check=True,capture_output=True,text=True)
    def test_build_independent_from_store(self):
        mk=(ROOT/'Makefile').read_text()
        self.assertIn('TITLE_ID   := CHEP00002',mk)
        self.assertIn('CHEPINSTALLER001',mk)
        workflow=(ROOT.parent/'.github/workflows/build-chepgame-installer.yml').read_text()
        self.assertIn('assets/libjbc.sprx',workflow)
        self.assertNotIn('ChepGameStore-PS4',workflow)
    def test_hdd_scan_is_explicit_and_covers_fallback(self):
        main=(ROOT/'src/main.cpp').read_text()
        install=(ROOT/'src/installer.cpp').read_text()
        self.assertIn('scan_package_locations(locations,files,error)',main)
        self.assertIn('/data/ChepGameStore/downloads',main)
        self.assertIn('/data/ChepGameStore/downloads/',install)
        self.assertLess(main.index('if(refresh){'),main.index('enable_hdd_scan_access()',main.index('if(refresh){')))
        self.assertIn('if(!read_pkg_info(path,st))continue;', (ROOT/'src/pkg_scan.cpp').read_text())

    def test_no_embedded_font_file(self):
        self.assertFalse(list(ROOT.rglob('*.ttf')))
        self.assertTrue((ROOT/'src/glyph_data.inc').stat().st_size>50000)
    def test_installer_never_uninstalls_games(self):
        code=(ROOT/'src/installer.cpp').read_text()
        self.assertNotIn('AppUnInstall',code)
        self.assertNotIn('remove(absolute_path',code)
        self.assertNotIn('remove(path',code)
        self.assertNotIn('unlink(',code)
        self.assertIn('sceBgftServiceIntDownloadRegisterTaskByStorageEx',code)
        self.assertIn('JBC_MISSING_OR_FAILED',code)
if __name__=='__main__':unittest.main()
