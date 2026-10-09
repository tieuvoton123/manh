import json
import struct
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prepare_native import prepare, valid_url, CONTENT_ID


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        for sub in ("src", "tools", "catalog", ".github/workflows"):
            (self.source / sub).mkdir(parents=True, exist_ok=True)
        (self.source / "src/main.cpp").write_text('''
#include "catalog.hpp"
const char* kCatalogUrl = "https://raw.githubusercontent.com/apexlions16/OrbisShelf/main/catalog/catalog.json";
const char* kCache = "/data/OrbisShelf/catalog.json";
const char* kDownloadDirectory = "/data/OrbisShelf/downloads";
enum JobType { JobRefresh, JobInstall };
std::string trim(std::string x) { return x; }

void* job_main(void*) {
    orbisshelf::HttpClient http;
    std::string error;
}
std::string optional_hf_token() {
    http.get_text(kCatalogUrl, 2 * 1024 * 1024, json, error);
    SDL_CreateWindow("OrbisShelf", 0);
    "ORBISSHELF";
    const SDL_Color background = {13, 18, 28, 255};
    const SDL_Color panel = {24, 32, 46, 255};
    const SDL_Color selected_color = {45, 112, 196, 255};
    const SDL_Color muted = {150, 164, 184, 255};
    const SDL_Color accent = {82, 193, 170, 255};
struct SharedState {
    int32_t last_error_code;
    bool job_running;
    std::string status;
    uint64_t current, total;
    std::vector<CatalogItem> items;
    pthread_mutex_t mutex;
    SharedState() : job_running(false), status("STARTING"), current(0), total(0), last_error_code(0) {
       pthread_mutex_init(&mutex, 0);
    }
};
void set_status(SharedState* state, const std::string& status, bool running, int32_t error_code = 0) {
    pthread_mutex_lock(&state->mutex);
    state->status = status;
    state->job_running = running;
    state->last_error_code = error_code;
    if (!running) { state->current = 0; state->total = 0; }
    pthread_mutex_unlock(&state->mutex);
}
void progress_callback(uint64_t current, uint64_t total, void* user) {
    SharedState* state = static_cast<SharedState*>(user);
    pthread_mutex_lock(&state->mutex);
    state->current = current;
    state->total = total;
    pthread_mutex_unlock(&state->mutex);
}
std::string truncate_text(const std::string& value, size_t max_chars) {
    if (value.size() <= max_chars) return value;
    if (max_chars < 4) return value.substr(0, max_chars);
    return value.substr(0, max_chars - 3) + "...";
}


void render(SDL_Renderer* renderer, SharedState& state, int selected) {
    orbisshelf::draw_text(renderer, 70, 38, 7, "ORBISSHELF", white);
    orbisshelf::draw_text(renderer, 1370, 48, 3, "X DOWNLOAD+INSTALL   TRIANGLE REFRESH   CIRCLE EXIT", muted);
}

} // namespace

    set_status(state, "DOWNLOADING " + item.name, true);
    return 0;
}

bool start_job(SharedState& state, JobType type, const CatalogItem* item) {
    state.status = type == JobRefresh ? "STARTING CATALOG REFRESH" : "STARTING DOWNLOAD";
    start_job(state, JobRefresh, 0);
    int selected = 0;
        while (SDL_PollEvent(&event)) {
            bool up = false, down = false, choose = false, refresh = false, quit = false;
                refresh = event.key.keysym.sym == SDLK_r;
                refresh = event.jbutton.button == 3;
            if (up && count) selected = (selected + count - 1) % count;
            if (refresh && !busy) start_job(state, JobRefresh, 0);
            if (choose && count && !busy) start_job(state, JobInstall, &chosen);
        render(renderer, state, selected);
    }
}
''', encoding="utf-8")
        (self.source / "src/sha256.cpp").write_text('std::string msg = "failed while hashing downloaded file";\n', encoding="utf-8")
        (self.source / "src/http_client.cpp").write_text('std::string msg = "sceHttpInit failed";\n', encoding="utf-8")
        (self.source / "src/catalog.cpp").write_text('''
bool valid_type(const std::string& value) {
if (item.id.empty() || item.name.empty() || item.pkg_url.compare(0, 8, "https://") != 0) {
}
''', encoding="utf-8")
        (self.source / "Makefile").write_text('''
TITLE       := OrbisShelf
VERSION     := 0.20
TITLE_ID    := ORBS00001
CONTENT_ID  := IV0000-ORBS00001_00-ORBISSHELF000001
$(INTDIR)/OrbisShelf.elf
$(INTDIR)/OrbisShelf.elf
CPPFILES := $(wildcard $(PROJDIR)/*.cpp)
LIBS := -lSceAppInstUtil -lSceBgft -lSDL2
PACKAGE_ASSETS := catalog.json
''', encoding="utf-8")
        (self.source / "LICENSE").write_text("MIT License\n", encoding="utf-8")
        (self.source / ".github/workflows/build.yml").write_text("unwanted upstream workflow", encoding="utf-8")
        (self.source / "catalog/catalog.json").write_text('{"items":[{"name":"unsafe upstream entry"}]}', encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_output(self):
        prepare(self.source, ROOT, "https://store.example.com/orbis/catalog.json")
        main = (self.source / "src/main.cpp").read_text()
        cat = (self.source / "src/catalog.cpp").read_text()
        make = (self.source / "Makefile").read_text()
        self.assertIn('CHEPGAME.NET', main)
        self.assertIn('TẢI HOÀN TẤT', main)
        self.assertIn('install_prompt', main)
        self.assertIn('CÀI NGAY', main)
        self.assertIn('Không tải được danh sách', (ROOT / 'chepgame_finish_ui.py').read_text(encoding='utf-8'))
        self.assertIn('current_catalog_url()', main)
        self.assertIn('chepgame::UrlEditor', main)
        self.assertIn('url_editor.input(event)', main)
        self.assertIn('url_editor.draw(renderer)', main)
        self.assertIn('edit_url = event.jbutton.button == 2', main)
        self.assertIn('start_job(state, JobRefresh, 0)', main)
        self.assertIn('CHEPGAME.NET', main)
        self.assertTrue((self.source / 'src/chepgame_url_ui.cpp').is_file())
        self.assertTrue((self.source / 'src/pixel_font.cpp').is_file())
        self.assertIn('/data/ChepGameStore/catalog_url.txt', main)
        self.assertIn('https://store.example.com/orbis/catalog.json', main)
        self.assertIn('safe_filename_piece', cat)
        self.assertIn('const char* kDownloadDirectory = "/data/pkg";', main)
        self.assertIn('const std::string staged_path = pkg_path + ".downloading";', main)
        self.assertIn('http.download(item.pkg_url, staged_path.c_str()', main)
        self.assertIn('rename(staged_path.c_str(), pkg_path.c_str())', main)
        self.assertIn('Tải hoàn tất', main)
        self.assertNotIn('STARTING LOCAL INSTALL', main)
        self.assertNotIn('INSTALL COMPLETE - LOCAL PKG DELETED', main)
        self.assertNotIn('installer.install_local(', main)
        self.assertIn('filter-out $(PROJDIR)/pkg_installer.cpp', make)
        self.assertIn('-lSceAppInstUtil -lSceBgft ', make)
        self.assertIn('CONTENT_ID  := ' + CONTENT_ID, make)
        self.assertEqual(make.count('$(INTDIR)/ChepGameStore.elf'), 2)
        self.assertNotIn('$(INTDIR)/OrbisShelf.elf', make)
        self.assertEqual(json.loads((self.source / "catalog/catalog.json").read_text())["items"], [])
        self.assertEqual(json.loads((self.source / "catalog.json").read_text())["items"], [])
        self.assertTrue((self.source / "tools/chepgame_icon.png").stat().st_size > 1000)
        # The compiled PS4 icon must be the new chibi asset, not the old text-only icon.
        generated_icon=(self.source / "tools/chepgame_icon.png").read_bytes()
        master_icon=(ROOT / "assets/chepgame_icon.png").read_bytes()
        self.assertEqual(hashlib.sha256(generated_icon).digest(), hashlib.sha256(master_icon).digest())
        self.assertEqual(generated_icon[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", generated_icon[16:24]), (512,512))
        self.assertFalse((self.source / ".github").exists())
        self.assertIn("(value.find('\\n')", main.replace(' &&', ' &&')) if False else None
        self.assertIn('value.find(\'\\n\')', main)

    def test_reject_changed_upstream(self):
        (self.source / "Makefile").write_text('TITLE := OTHER\n')
        with self.assertRaises(RuntimeError):
            prepare(self.source, ROOT, "https://store.example.com/catalog.json")

    def test_reject_bad_urls(self):
        for url in ('file:///var/data', 'ftp://example.com/store', 'https://user:pass@host.com/x',
                    'https://example.com/has space', 'https://example.com/"x"'):
            with self.assertRaises(ValueError, msg=url):
                valid_url(url)
        self.assertEqual(valid_url('https://example.com/s'), 'https://example.com/s')
        self.assertEqual(valid_url('http://192.168.1.5:8099/orbis/catalog.json'),
                         'http://192.168.1.5:8099/orbis/catalog.json')

    def test_pipeline(self):
        content=(ROOT / ".github/workflows/build-ps4.yml").read_text()
        self.assertIn('workflow_dispatch:', content)
        self.assertIn('prepare_native.py', content)
        self.assertIn('toolchain-llvm-18.tar.gz', content)
        self.assertIn('upload-artifact@v4', content)
        self.assertIn('ChepGameStore-PS4-v0.4.5.pkg', content)


if __name__ == "__main__":
    unittest.main()
