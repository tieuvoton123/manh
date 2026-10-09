#!/usr/bin/env python3
"""Prepare independent PS4 ChepGame Store homebrew sources from pinned MIT-licensed OrbisShelf.

No commercial PKGs are bundled. Compiling requires OpenOrbis; this script is a source generator.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

UPSTREAM = "https://github.com/apexlions16/OrbisShelf.git"
PINNED_COMMIT = "d63ada1a21bd780e79380ee120554f5aebcb2fcd"
TITLE_ID = "CHEP00001"
CONTENT_ID = "IV0000-CHEP00001_00-CHEPGAMESTORE001"
DEFAULT_CATALOG = "http://192.168.1.6:8099/orbis/catalog.json"


def valid_url(value: str) -> str:
    value = value.strip()
    parsed = urlsplit(value)
    if (parsed.scheme not in ("https", "http") or not parsed.hostname or
        parsed.username is not None or parsed.password is not None or
        any(ch in value for ch in '\\"\r\n\x00<> ')):
        raise ValueError("URL phải bắt đầu bằng https:// (hoặc http:// trong LAN), không có khoảng trắng/nháy")
    if len(value) > 1700:
        raise ValueError("Đường dẫn catalog quá dài")
    return value


def patch_exact(path: Path, old: str, new: str, count: int | None = None) -> None:
    source = path.read_text(encoding="utf-8-sig")
    actual = source.count(old)
    if actual == 0 or (count is not None and actual != count):
        raise RuntimeError(f"Mã nguồn upstream đã đổi: {path.name}, yêu cầu {count} xuất hiện, tìm {actual}: {old[:90]!r}")
    path.write_text(source.replace(old, new), encoding="utf-8")


def get_sources(root: Path, local_source: str = "") -> None:
    if local_source:
        shutil.copytree(Path(local_source).resolve(), root,
                        ignore=shutil.ignore_patterns(".git", "build", "*.pkg", "eboot.bin"))
    else:
        root.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "remote", "add", "origin", UPSTREAM], check=True)
        subprocess.run(["git", "-C", str(root), "fetch", "-q", "--depth", "1", "origin", PINNED_COMMIT], check=True)
        subprocess.run(["git", "-C", str(root), "checkout", "-q", "--detach", "FETCH_HEAD"], check=True)
        real = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        if real != PINNED_COMMIT:
            raise RuntimeError("Mã nguồn upstream không đúng commit đã kiểm tra")
        shutil.rmtree(root / ".git")


def prepare(source: Path, bundle_root: Path, catalog_url: str) -> None:
    # Never include the upstream's pre-populated catalog; only explicit, authorized additions.
    data = {"schema_version": 1, "generated_at": "2026-10-09T00:00:00Z", "items": []}
    (source / "catalog").mkdir(parents=True, exist_ok=True)
    for filename in (source / "catalog" / "catalog.json", source / "catalog.json"):
        filename.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    main = source / "src" / "main.cpp"
    mk = source / "Makefile"
    assert main.is_file() and mk.is_file() and (source / "src" / "catalog.cpp").is_file(), "Thiếu source OrbisShelf"
    patch_exact(main,
                'const char* kCatalogUrl = "https://raw.githubusercontent.com/apexlions16/OrbisShelf/main/catalog/catalog.json";',
                f'const char* kDefaultCatalogUrl = {json.dumps(catalog_url)};\n'
                'const char* kCustomCatalogUrl = "/data/ChepGameStore/catalog_url.txt";', 1)
    patch_exact(main, "/data/OrbisShelf", "/data/ChepGameStore")
    patch_exact(main, "ORBISSHELF", "CHEPGAME.NET")
    patch_exact(main, '#include "catalog.hpp"', '#include "catalog.hpp"\n#include "chepgame_url_ui.hpp"', 1)
    patch_exact(main, 'SDL_CreateWindow("OrbisShelf"', 'SDL_CreateWindow("ChepGame Store"', 1)
    # User can update remote source through GoldHEN FTP, without needing to rebuild the PKG.
    selector = '''
std::string current_catalog_url() {
    std::string value, error;
    if (orbisshelf::load_text_file(kCustomCatalogUrl, value, error)) {
        value = trim(value);
        if ((value.compare(0, 8, "https://") == 0 ||
             value.compare(0, 7, "http://") == 0) && value.size() < 1700 &&
             value.find(' ') == std::string::npos && value.find('\\n') == std::string::npos)
            return value;
    }
    return std::string(kDefaultCatalogUrl);
}

'''
    patch_exact(main, 'std::string optional_hf_token() {', selector + 'std::string optional_hf_token() {', 1)
    patch_exact(main, 'http.get_text(kCatalogUrl, 2 * 1024 * 1024, json, error)',
                'http.get_text(current_catalog_url(), 2 * 1024 * 1024, json, error)', 1)
    patch_exact(main, 'const SDL_Color background = {13, 18, 28, 255};',
                'const SDL_Color background = {28, 7, 8, 255};', 1)
    patch_exact(main, 'const SDL_Color panel = {24, 32, 46, 255};',
                'const SDL_Color panel = {65, 14, 12, 255};', 1)
    patch_exact(main, 'const SDL_Color muted = {150, 164, 184, 255};',
                'const SDL_Color muted = {240, 179, 124, 255};', 1)
    patch_exact(main, 'const SDL_Color selected_color = {45, 112, 196, 255};',
                'const SDL_Color selected_color = {180, 30, 18, 255};', 1)
    patch_exact(main, 'const SDL_Color accent = {82, 193, 170, 255};',
                'const SDL_Color accent = {255, 214, 70, 255};', 1)
    patch_exact(mk, 'TITLE       := OrbisShelf', 'TITLE       := ChepGame.NET', 1)
    patch_exact(mk, 'VERSION     := 0.20', 'VERSION     := 0.34', 1)
    patch_exact(mk, 'TITLE_ID    := ORBS00001', 'TITLE_ID    := ' + TITLE_ID, 1)
    patch_exact(mk, 'CONTENT_ID  := IV0000-ORBS00001_00-ORBISSHELF000001',
                'CONTENT_ID  := ' + CONTENT_ID, 1)
    # Original pinned Makefile uses the ELF path twice: as linker output and as create-fself input.
    # Both must be renamed together or the compiler/linker targets will disagree.
    patch_exact(mk, '$(INTDIR)/OrbisShelf.elf', '$(INTDIR)/ChepGameStore.elf', 2)
    # v0.3.3: GoldHEN 2.4b18.9 supports internal package installation at
    # /data/pkg. Use download-only, bypassing the privileged AppInstUtil/BGFT
    # calls which previously failed or risked instability on this firmware.
    patch_exact(main,
                'const char* kDownloadDirectory = "/data/ChepGameStore/downloads";',
                'const char* kDownloadDirectory = "/data/pkg";', 1)
    patch_exact(mk,
                'CPPFILES := $(wildcard $(PROJDIR)/*.cpp)',
                'CPPFILES := $(filter-out $(PROJDIR)/pkg_installer.cpp,$(wildcard $(PROJDIR)/*.cpp))', 1)
    # Keep the SDK link libraries: legacy BGFT functions are still compiled
    # and referenced by the current UI even though direct install is disabled.

    # Keep .pkg invisible to GoldHEN while incomplete: download to .downloading
    # and atomically rename only after size/SHA256 checks pass. No overwrites.
    cpp = main.read_text(encoding='utf-8')
    start_key = '    set_status(state, "DOWNLOADING " + item.name, true);'
    end_key = '\n}\n\nbool start_job(SharedState& state, JobType type, const CatalogItem* item) {'
    if cpp.count(start_key) != 1 or cpp.count(end_key) != 1:
        raise RuntimeError('Pinned main.cpp download function layout changed; refuse to patch')
    start_at = cpp.index(start_key)
    end_at = cpp.index(end_key, start_at)
    replacement = r'''    set_status(state, "DOWNLOADING " + item.name, true);
    const std::string pkg_path = std::string(kDownloadDirectory) + "/" + item.id + "-" + item.version + ".pkg";
    const std::string staged_path = pkg_path + ".downloading";
    struct stat pkg_stat;
    if (stat(pkg_path.c_str(), &pkg_stat) == 0) {
        // Never replace an existing (possibly user-owned) PKG from FTP/GoldHEN.
        set_status(state, "PKG ALREADY IN /DATA/PKG - NOT OVERWRITTEN", false);
        return 0;
    }
    if (errno != ENOENT) {
        set_status(state, "CANNOT ACCESS /DATA/PKG - CHECK PERMISSIONS", false);
        return 0;
    }

    uint64_t downloaded = 0;
    const std::string token = optional_hf_token();
    if (!http.download(item.pkg_url, staged_path.c_str(), progress_callback, state, downloaded, error, token)) {
        set_status(state, "DOWNLOAD FAILED: " + error, false);
        return 0;
    }
    if (item.size_bytes && downloaded != item.size_bytes) {
        remove(staged_path.c_str());
        set_status(state, "SIZE CHECK FAILED - NO PKG PUBLISHED", false);
        return 0;
    }
    if (!item.sha256.empty()) {
        set_status(state, "VERIFYING SHA256", true);
        std::string digest;
        if (!orbisshelf::sha256_file(staged_path.c_str(), digest, error) || digest != item.sha256) {
            remove(staged_path.c_str());
            set_status(state, "SHA256 CHECK FAILED - NO PKG PUBLISHED", false);
            return 0;
        }
    }
    // Another process (FTP) may have added the file while downloading.
    if (stat(pkg_path.c_str(), &pkg_stat) == 0 || errno != ENOENT) {
        remove(staged_path.c_str());
        set_status(state, "PKG FILE ALREADY EXISTS - NOT OVERWRITTEN", false);
        return 0;
    }
    // Both paths live within /data/pkg, so rename is atomic and avoids a second
    // full-size copy. GoldHEN will only see the verified .pkg filename.
    if (rename(staged_path.c_str(), pkg_path.c_str()) != 0) {
        // Staging file is deliberately retained for FTP recovery.
        set_status(state, "FINALIZE PKG FAILED - CHECK /DATA/PKG", false);
        return 0;
    }
    set_status(state, "PKG READY IN /DATA/PKG - OPEN GOLDHEN PACKAGE INSTALLER", false);
    return 0;'''
    cpp = cpp[:start_at] + replacement + cpp[end_at:]
    cpp = cpp.replace('#include <cstdio>','#include <cstdio>\n#include <cerrno>',1)
    main.write_text(cpp, encoding='utf-8')

    # New native URL-entry screen. Compiled by the upstream Makefile's src/*.cpp wildcard.
    shutil.copyfile(bundle_root / 'chepgame_url_ui.hpp', source / 'src' / 'chepgame_url_ui.hpp')
    shutil.copyfile(bundle_root / 'chepgame_url_ui.cpp', source / 'src' / 'chepgame_url_ui.cpp')
    patch_exact(main, '    start_job(state, JobRefresh, 0);\n    int selected = 0;',
        '''    chepgame::UrlEditor url_editor(current_catalog_url());
    bool url_screen = true;
    int selected = 0;''', 1)
    patch_exact(main, '        while (SDL_PollEvent(&event)) {',
        '''        while (SDL_PollEvent(&event)) {
            if (url_screen) {
                const chepgame::UrlAction action = url_editor.input(event);
                if (action == chepgame::UrlConnect) {
                    if (save_text(kCustomCatalogUrl, url_editor.value() + "\\n")) {
                        url_screen = false;
                        start_job(state, JobRefresh, 0);
                    } else {
                        url_editor.error("CANNOT SAVE URL - CHECK STORAGE");
                    }
                } else if (action == chepgame::UrlCancel) {
                    url_screen = false;
                    start_job(state, JobRefresh, 0);
                }
                continue;
            }''', 1)
    patch_exact(main, '            bool up = false, down = false, choose = false, refresh = false, quit = false;',
        '            bool up = false, down = false, choose = false, refresh = false, quit = false, edit_url = false;', 1)
    patch_exact(main, '                refresh = event.key.keysym.sym == SDLK_r;',
        '                refresh = event.key.keysym.sym == SDLK_r;\n                edit_url = event.key.keysym.sym == SDLK_u;', 1)
    patch_exact(main, '                refresh = event.jbutton.button == 3;',
        '                refresh = event.jbutton.button == 3;\n                edit_url = event.jbutton.button == 2;', 1)
    patch_exact(main, '            if (refresh && !busy) start_job(state, JobRefresh, 0);',
        '''            if (edit_url && !busy) {
                url_editor.reset(current_catalog_url());
                url_screen = true;
                continue;
            }
            if (refresh && !busy) start_job(state, JobRefresh, 0);''', 1)
    patch_exact(main, '        render(renderer, state, selected);',
        '        if (url_screen) url_editor.draw(renderer);\n        else render(renderer, state, selected);', 1)
    patch_exact(main, 'orbisshelf::draw_text(renderer, 1370, 48, 3, "X DOWNLOAD+INSTALL   TRIANGLE REFRESH   CIRCLE EXIT", muted);',
        'orbisshelf::draw_text(renderer, 1240, 48, 2, "X DOWNLOAD / TRIANGLE REFRESH / SQUARE URL", muted);', 1)
    patch_exact(main, 'orbisshelf::draw_text(renderer, 70, 38, 7, "CHEPGAME.NET", white);',
        'orbisshelf::draw_text(renderer, 70, 36, 7, "CHEPGAME.NET", accent);\n    orbisshelf::draw_text(renderer, 625, 57, 3, "BY SUPER MANH", white);', 1)
    dest_icon = source / 'tools' / 'chepgame_icon.png'
    dest_icon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(bundle_root / 'assets' / 'chepgame_icon.png', dest_icon)
    (source / 'tools' / 'generate_icon.py').write_text('''#!/usr/bin/env python3
import shutil, sys
from pathlib import Path
out = Path(sys.argv[1]); out.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(Path(__file__).with_name("chepgame_icon.png"), out)
''', encoding="utf-8")
    # Upstream actions must not publish to an upstream repository or release.
    shutil.rmtree(source / '.github', ignore_errors=True)
    (source / 'CHEPGAME_INFO.txt').write_text(
        'ChepGame Store v0.4.0: Three BGFT/Bato-style workflows\n'
        'Based on OrbisShelf (MIT). See LICENSE.\n'
        'Catalog built-in URL: ' + catalog_url + '\n'
        'Override URL: /data/ChepGameStore/catalog_url.txt\n'
        'Output PKG directory: /data/pkg\n'
        'Mode: X download to /data/pkg; R1 active tab; BGFT install is experimental.\n'
        'Only distribute PKGs with permission.\n', encoding='utf-8')
    # Security: avoid relative path traversal in server-controlled package IDs/versions.
    catalog = source / 'src' / 'catalog.cpp'
    safe = '''
bool safe_filename_piece(const std::string& value) {
    if (value.empty() || value.size() > 100) return false;
    for (size_t i=0; i < value.size(); ++i) {
        const char c = value[i];
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
              (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.')) return false;
    }
    return value != "." && value != ".." && value.find("..") == std::string::npos;
}

'''
    patch_exact(catalog, 'bool valid_type(const std::string& value) {',
                safe + 'bool valid_type(const std::string& value) {', 1)
    patch_exact(catalog,
                'if (item.id.empty() || item.name.empty() || item.pkg_url.compare(0, 8, "https://") != 0) {',
                'if (!safe_filename_piece(item.id) || !safe_filename_piece(item.version) || item.name.empty() ||\n'
                '                (item.pkg_url.compare(0, 8, "https://") != 0 &&\n'
                '                 item.pkg_url.compare(0, 7, "http://") != 0)) {', 1)
    from chepgame_finish_ui import apply as finish_ui
    finish_ui(source, bundle_root)
    from chepgame_polish_v035 import apply as polish_ui
    polish_ui(source, bundle_root)
    from chepgame_base_text_patch import apply as apply_base_text
    apply_base_text(source, bundle_root)
    from chepgame_layout_speed_v0373 import apply as apply_layout_speed
    apply_layout_speed(source, bundle_root)
    from chepgame_bgft_mode_v038 import apply as apply_bgft_remote
    apply_bgft_remote(source, bundle_root)
    from chepgame_system_font_v039 import apply as apply_system_font
    apply_system_font(source, bundle_root)
    from chepgame_safe_exit_v0391 import apply as apply_safe_exit
    apply_safe_exit(source, bundle_root)
    from chepgame_bgft_probe_v0392 import apply as apply_bgft_probe
    apply_bgft_probe(source, bundle_root)
    from chepgame_three_modes_v040 import apply as apply_three_modes
    apply_three_modes(source, bundle_root)
    from chepgame_bgft_themeprobe_v041 import apply as apply_theme_probe
    apply_theme_probe(source, bundle_root)
    from chepgame_fast_download_v042 import apply as apply_fast_download
    apply_fast_download(source, bundle_root)
    from chepgame_download_stable_v043 import apply as apply_stable
    apply_stable(source, bundle_root)
    from chepgame_download_audit_v044 import apply as apply_audit
    apply_audit(source, bundle_root)
    print('Đã chuẩn bị mã nguồn homebrew PS4:', source)
    print('Biên dịch: export OO_PS4_TOOLCHAIN=... && make')
    print('Tên PKG dự kiến: ' + CONTENT_ID + '.pkg')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--catalog-url', default=DEFAULT_CATALOG, help='URL danh sách PKG. Cần HTTPS nếu dùng trên Internet.')
    ap.add_argument('--out', default='ChepGameStore-PS4')
    ap.add_argument('--source', default='', help='Đường dẫn OrbisShelf đã tải sẵn (tùy chọn)')
    args = ap.parse_args()
    try:
        catalog_url = valid_url(args.catalog_url)
    except ValueError as exc:
        ap.error(str(exc))
    target = Path(args.out).absolute()
    if target.exists():
        ap.error(f'Thư mục đã tồn tại (không ghi đè): {target}')
    try:
        get_sources(target, args.source)
        prepare(target, Path(__file__).resolve().parent, catalog_url)
    except Exception:
        print('Lỗi khi chuẩn bị mã nguồn. Kiểm tra log. Thư mục chưa hoàn thành:', target)
        raise


if __name__ == '__main__':
    main()
