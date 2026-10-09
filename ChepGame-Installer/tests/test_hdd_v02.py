import pathlib
import unittest
R = pathlib.Path(__file__).resolve().parents[1]
S = (R / "src" / "installer.cpp").read_text()
M = (R / "src" / "main.cpp").read_text()
SCAN = (R / "src" / "pkg_scan.cpp").read_text()
MK = (R / "Makefile").read_text()
WF = (R.parent / ".github" / "workflows" / "build-chepgame-installer.yml").read_text()

class InstallerSafetyTests(unittest.TestCase):
    def test_only_local_hdd_storage(self):
        self.assertIn('"/data/pkg/"', S)
        self.assertIn('"/data/pkg"', M)
        self.assertNotIn('http://', S)
        self.assertNotIn('https://', S)

    def test_double_confirmation_throttled(self):
        self.assertIn('last_confirm_press', M)
        self.assertIn('now-last_confirm_press<400', M)
        self.assertIn('e.key.repeat', M)
        self.assertIn('if(confirm)', M)

    def test_pkg_header_and_symlink_safe(self):
        self.assertIn('O_NOFOLLOW', S)
        self.assertIn('O_NOFOLLOW', SCAN)
        self.assertIn('st.st_ino', SCAN)
        self.assertIn('pkg.inode', SCAN)
        self.assertIn('fstat(fd,&checked)', S)
        self.assertIn('0x7f', S)
        self.assertIn('lstat(', S)

    def test_never_claim_install_success_on_task_registration(self):
        self.assertIn('TASK_ACCEPTED_NOT_INSTALLED', S)
        self.assertIn('Đã gửi tác vụ cho PS4; chưa xác nhận cài xong', M)
        self.assertNotIn('INSTALLED_SUCCESS', S)

    def test_bgft_polling_error_stops(self):
        self.assertIn('progress_failed=true', M)
        self.assertIn('started && can_poll && !progress_failed', M)

    def test_optional_jbc_module_validation(self):
        self.assertIn('diagnostic_without_jbc', WF)
        self.assertIn('python3 fetch_jbc.py', WF)
        self.assertIn('test -s assets/libjbc.sprx', WF)
        self.assertIn('sceKernelDlsym(handle,"Jailbreak"', S)

    def test_disk_check_fails_closed(self):
        self.assertIn('FREE_SPACE_CHECK_FAILED', S)
        self.assertIn('INSUFFICIENT_FREE_SPACE', S)
    def test_app_is_separate(self):
        self.assertIn('TITLE_ID   := CHEP00002', MK)
        self.assertIn('VERSION    := 0.33', MK)
        self.assertIn('PS4-v0.3.3', WF)
        self.assertIn('sceBgftServiceIntDownloadRegisterTaskByStorageEx', S)

    def test_no_destructive_install(self):
        self.assertNotIn('sceAppInstUtilAppUnInstall', S)
        self.assertNotIn('unlink(', S)
        self.assertNotIn('remove(absolute_path', S)
        self.assertNotIn('remove(path', S)
        self.assertNotIn('unlink(', S)

if __name__ == "__main__":
    unittest.main()
