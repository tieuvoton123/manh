"""v0.4.4: repair PS4 directory preflight and safe existing-PKG detection.

Run AFTER chepgame_download_stable_v043:apply, not on the upstream source.
"""
from pathlib import Path
import shutil


def once(s, old, new):
    n = s.count(old)
    if n != 1:
        raise RuntimeError('v0.4.4 patch mismatch (%d): %s' % (n, old[:100]))
    return s.replace(old, new, 1)


def apply(source: Path, root: Path):
    shutil.copyfile(root/'chepgame_download_fs.hpp', source/'src/chepgame_download_fs.hpp')
    p = source/'src/main.cpp'
    s = p.read_text(encoding='utf-8')
    s = once(s, '#include "chepgame_url_ui.hpp"',
             '#include "chepgame_url_ui.hpp"\n#include "chepgame_download_fs.hpp"')
    begin = s.index('    if(type==JobInstall) {\n        chepgame_download_log("CHECK"')
    finish = s.index('    orbisshelf::HttpClient http;', begin)
    new = '''    // Resolve the real write destination BEFORE touching HTTP. PS4 libc may
    // return a nonportable errno after lstat("/data/pkg/file").
    std::string chepgame_target_dir = kDownloadDirectory;
    bool chepgame_using_fallback = false;
    if(type==JobInstall) {
        const std::string primary = kDownloadDirectory;
        const std::string fallback = "/data/ChepGameStore/downloads";
        const std::string suffix = "/"+item.id+"-"+item.version+".pkg";
        // Do not replace an existing file, even if it is in the fallback.
        // A header alone cannot prove complete if catalog size is unknown.
        for(int where=0; where<2; ++where) {
            const std::string directory = where==0 ? primary : fallback;
            const std::string existing = directory+suffix;
            uint64_t length=0;
            struct stat st;
            if(lstat(existing.c_str(),&st)==0) {
                if(!chepgame::regular_file(existing,length)) {
                    set_status(state,"PKG đích không phải file thường; không ghi đè",false);
                    chepgame_download_log("UNSAFE_TARGET",0,item.size_bytes);
                    return 0;
                }
                if(item.size_bytes && length!=item.size_bytes) {
                    set_status(state,"Đã có PKG nhưng dung lượng không khớp; không ghi đè",false);
                    chepgame_download_log("SIZE_EXISTING_MISMATCH",length,item.size_bytes);
                    return 0;
                }
                if(!chepgame::pkg_magic_ok(existing)) {
                    set_status(state,"Đã có PKG nhưng header lỗi; không ghi đè",false);
                    chepgame_download_log("HEADER_EXISTING_INVALID",length,item.size_bytes);
                    return 0;
                }
                if(item.size_bytes==0 && item.sha256.empty()) {
                    set_status(state,"Đã có PKG chưa rõ dung lượng; kiểm tra trước khi dùng",false);
                    chepgame_download_log("EXISTING_UNVERIFIED",length,0);
                    return 0;
                }
                if(!item.sha256.empty()) {
                    std::string existing_sha, existing_error;
                    if(!orbisshelf::sha256_file(existing.c_str(),existing_sha,existing_error) ||
                       existing_sha!=item.sha256) {
                        set_status(state,"PKG đã có nhưng SHA-256 không khớp; không ghi đè",false);
                        chepgame_download_log("EXISTING_SHA_MISMATCH",length,item.size_bytes);
                        return 0;
                    }
                }
                if(where==0) set_status(state,"PKG đã có trong /data/pkg – không tải lại",false);
                else set_status(state,"PKG đã có tại /data/ChepGameStore/downloads – chuyển bằng FTP",false);
                chepgame_download_log("EXISTS_VERIFIED",length,item.size_bytes);
                return 0;
            }
        }
        std::string primary_diagnostic, fallback_diagnostic;
        int primary_code=0, fallback_code=0;
        const bool primary_ok=chepgame::ensure_writable_dir(primary,primary_diagnostic,primary_code);
        // Never switch away from an existing partial file, to avoid invisible
        // duplicate downloads when directory permissions change.
        if(primary_ok) {
            chepgame_target_dir=primary;
        } else if(chepgame::ensure_writable_dir(fallback,fallback_diagnostic,fallback_code)) {
            chepgame_target_dir=fallback;
            chepgame_using_fallback=true;
            chepgame_download_log("FALLBACK_DIR",(uint64_t)primary_code,0);
        } else {
            set_status(state,"Không ghi được HDD. /data/pkg:"+std::to_string(primary_code)+
                       " Store:"+std::to_string(fallback_code)+"; xem tai_pkg.log",false);
            chepgame_download_log("DIR_BOTH_FAILED",(uint64_t)primary_code,(uint64_t)fallback_code);
            return 0;
        }
        // If the inaccessible primary has a partially-downloaded PKG, don't
        // silently restart it in a different directory.
        if(chepgame_using_fallback && chepgame::file_entry_exists(primary+suffix+".downloading")) {
            set_status(state,"Có PKG tải dở ở /data/pkg nhưng không thể ghi tiếp; kiểm tra FTP",false);
            return 0;
        }
    }
'''
    s=s[:begin]+new+s[finish:]
    # Keep all paths in the same dir and do not hardcode /data/pkg in the success message.
    s=once(s, 'std::string(kDownloadDirectory) + "/" + item.id + "-" + item.version + ".pkg";',
           'chepgame_target_dir + "/" + item.id + "-" + item.version + ".pkg";')
    # Patch early finalize preflight: do not depend on errno after missing final file.
    # The destination already passed a direct write probe before the download.
    s=once(s, '''    if (stat(pkg_path.c_str(), &pkg_stat) == 0 || errno != ENOENT) {''',
        '''    if (chepgame::file_entry_exists(pkg_path)) {''')
    s=once(s, '''    std::remove((staged_path+".resume").c_str());
    chepgame_download_log("READY",downloaded,item.size_bytes);
    set_status(state, "Tải hoàn tất – PKG sẵn sàng tại /data/pkg", false);''',
        '''    std::remove((staged_path+".resume").c_str());
    chepgame_download_log(chepgame_using_fallback?"READY_FALLBACK":"READY",downloaded,item.size_bytes);
    set_status(state,chepgame_using_fallback?
               "Tải hoàn tất – lưu /data/ChepGameStore/downloads; mở ChepGame Installer để cài":
               "Tải hoàn tất – PKG sẵn sàng tại /data/pkg",false);''')
    s=once(s, '"100% – Đã lưu PKG vào /data/pkg"', '"100% – Đã lưu PKG vào HDD"')
    # Fix status if existing after download to avoid clobbering other files.
    s=once(s, 'BY SUPER MANH  v0.43', 'BY SUPER MANH  v0.45')
    p.write_text(s, encoding='utf-8')
    mk = source/'Makefile'
    mk.write_text(once(mk.read_text(encoding='utf-8'), 'VERSION     := 0.43','VERSION     := 0.45'),encoding='utf-8')
    with (source/'CHEPGAME_INFO.txt').open('a',encoding='utf-8') as f:
        f.write('v0.4.4: direct PS4 directory write-probe; no errno-only refusal; '
                'explicit fallback path; existing PKG not overwritten; strict preflight.\\n')
