"""v0.4.3 download completion / no-repeat fix, applied after v0.4.2.

Keep download-only + resume; require provable Content-Length, suppress input
repeat, retain success progress, keep partial data on transient failures.
"""
from pathlib import Path


def one(text, old, new):
    count = text.count(old)
    if count != 1:
        raise RuntimeError('v0.4.3 source mismatch (%d): %s' % (count, old[:110]))
    return text.replace(old, new, 1)


def upgrade_http_text(s: str) -> str:
    marker = '''        if(expected_size==0 && server_total>0) expected_size=server_total;'''
    s = one(s, marker, '''        // A PKG is complete only if the actual number of bytes is known.
        // The PC server returns Content-Length even when the catalog has no size.
        int length_kind=0;size_t body_length=0;
        const int length_rc=sceHttpGetResponseContentLength(handles.req,&length_kind,&body_length);
        if(status==200 && length_rc>=0 && body_length>0) {
            if(expected_size && uint64_t(body_length)!=expected_size) {
                close_request(handles);
                error="Dung lượng máy chủ khác với danh mục";
                return false;
            }
            server_total=uint64_t(body_length);
        }
        if(status==206 && length_rc>=0 && body_length>0 &&
           server_total>request_start && uint64_t(body_length)!=server_total-request_start) {
            close_request(handles);
            error="Máy chủ trả độ dài HTTP Range không khớp";
            return false;
        }
        if(expected_size==0 && server_total>0) expected_size=server_total;
        if(expected_size==0) {
            close_request(handles);
            error="Máy chủ không trả tổng dung lượng PKG";
            return false;
        }''')
    s = one(s, '        bool io_ok=true,match=true;', '        bool io_ok=true,match=true,network_read_error=false;')
    s = one(s, 'if(count<0) {error="Kết nối tải bị ngắt";io_ok=false;break;}',
            'if(count<0) {error="Kết nối tải bị ngắt";io_ok=false;network_read_error=true;break;}')
    s = one(s, '''        if(io_ok && (!expected_size || completed==expected_size)) {''', '''        // Some PS4 HTTP builds report a read error after delivering the last byte.
        // Count + flush + expected total (and later PKG/SHA check) decide completion.
        if((io_ok || network_read_error) && completed==expected_size &&
           overlap_checked==overlap.size()) {''')
    s = one(s, '''        if(io_ok && expected_size && completed<expected_size)error="Tải chưa đủ; đang tiếp tục";''', '''        if(!io_ok && !network_read_error) return false; // Disk/response error: do not loop.
        if(io_ok && completed<expected_size)error="Tải chưa đủ; đang tiếp tục";''')
    # Sanitize success: no stale error from a previous retry.
    s = one(s, '''            downloaded_bytes=completed;
            if(callback)callback(completed,expected_size,user);
            return true;
        }
        if(!io_ok && !network_read_error) return false;''', '''            downloaded_bytes=completed;
            error.clear();
            if(callback)callback(completed,expected_size,user);
            return true;
        }
        if(!io_ok && !network_read_error) return false;''')
    return s


def apply(source: Path, root: Path):
    http = source / 'src/http_client.cpp'
    # Unit fixtures only provide a dummy http_client.cpp; real code is verified separately.
    if 'bool HttpClient::download(' in http.read_text(encoding='utf-8'):
        http.write_text(upgrade_http_text(http.read_text(encoding='utf-8')),encoding='utf-8')

    main = source / 'src/main.cpp'
    s = main.read_text(encoding='utf-8')
    # Bounded diagnostics; never log source URLs or credentials.
    at=s.index('void* job_main(')
    s=s[:at]+"""void chepgame_download_log(const char* stage, uint64_t bytes, uint64_t total) {
    const char* path=\"/data/ChepGameStore/tai_pkg.log\";
    struct stat st;
    const bool truncate=lstat(path,&st)==0 && S_ISREG(st.st_mode) && st.st_size>131072;
    FILE* f=std::fopen(path,truncate?\"wb\":\"ab\");
    if(!f)return;
    std::fprintf(f,\"%u | %s | %llu/%llu\\n\",(unsigned)SDL_GetTicks(),stage,
                 (unsigned long long)bytes,(unsigned long long)total);
    std::fclose(f);
}

""".replace('\\"','"')+s[at:]
    s = one(s, '''    bool download_active = false;''',
            '''    bool download_active = false;
    bool download_finished = false;''')
    s = one(s, '''    if (!running) {
        state->current = state->total = 0;
        state->download_active = false;
        state->expected_size = 0;
        state->meter.reset();
    }''', '''    if (!running) {
        // 100% is a terminal state, not a signal to restart the transfer.
        const bool done = status.find("Tải hoàn tất") == 0;
        state->download_finished = done;
        if(done) {
            if(state->total) state->current=state->total;
        } else {
            state->current=state->total=0;
        }
        state->download_active=false;
        state->expected_size=0;
        state->meter.reset();
    }''')
    s = one(s, '''    state->download_active = true;
    state->expected_size = item.size_bytes;''',
            '''    state->download_active = true;
    state->download_finished = false;
    state->expected_size = item.size_bytes;''')
    # No network is needed to recognize an already finished PKG. Also reject non-regular
    # final entries rather than following an unexpected /data/pkg symlink.
    s = one(s, '''    orbisshelf::HttpClient http;
    std::string error;''', '''    if(type==JobInstall) {
        const std::string existing=std::string(kDownloadDirectory)+"/"+item.id+"-"+item.version+".pkg";
        struct stat existing_stat;
        if(lstat(existing.c_str(),&existing_stat)==0) {
            if(S_ISREG(existing_stat.st_mode) && existing_stat.st_size>=4 &&
               (!item.size_bytes || uint64_t(existing_stat.st_size)==item.size_bytes)) {
                FILE* f=std::fopen(existing.c_str(),"rb");
                unsigned char magic[4]={0};
                const bool valid=f && std::fread(magic,1,4,f)==4 &&
                    magic[0]==0x7f && magic[1]=='C' && magic[2]=='N' && magic[3]=='T';
                if(f) std::fclose(f);
                set_status(state,valid?"PKG đã có trong /data/pkg – không tải lại":
                           "PKG đã tồn tại nhưng header không hợp lệ",false);
            } else {
                set_status(state,"PKG đã tồn tại; kiểm tra tệp trước khi tải",false);
            }
            return 0;
        }
        if(errno!=ENOENT) {
            set_status(state,"Không thể kiểm tra thư mục /data/pkg",false);
            return 0;
        }
    }
    orbisshelf::HttpClient http;
    std::string error;''')
    # Retain evidence instead of deleting a huge staged PKG on size/hash/header error.
    s = one(s, '''        remove(staged_path.c_str());
        set_status(state, "Sai dung lượng. Đã hủy tệp tạm", false);''',
            '''        set_status(state, "Sai dung lượng; giữ .downloading để kiểm tra", false);''')
    s = one(s, '''            remove(staged_path.c_str());
            set_status(state, "Sai mã SHA-256. Đã hủy tệp tạm", false);''',
            '''            set_status(state, "SHA-256 không khớp; giữ tệp tạm để kiểm tra", false);''')
    s = one(s, '''            std::remove(staged_path.c_str());
            std::remove((staged_path+".resume").c_str());
            set_status(state,"Tệp tải về không phải PS4 PKG hợp lệ",false);''',
            '''            set_status(state,"Header PKG sai; giữ .downloading để kiểm tra",false);''')
    # Do not delete our staged file if an external process puts a PKG in the directory.
    s = one(s, '''        remove(staged_path.c_str());
        set_status(state, "PKG đã có, không ghi đè", false);''',
            '''        set_status(state, "PKG đã có, không ghi đè; giữ tệp tạm", false);''')
    # Preserve 100% even after disabling speed meter; no bar bouncing back to 0.
    s = one(s, '''    bool prompt=false,submitted=false,failed=false,busy=false,downloading=false;''',
            '''    bool prompt=false,submitted=false,failed=false,busy=false,downloading=false,completed_visible=false;''')
    s = one(s, '''    downloading=state.download_active;''', '''    downloading=state.download_active;
    completed_visible=state.download_finished;''')
    s = one(s, '''    } else if (total && downloading) {''', '''    } else if (total && (downloading || completed_visible)) {''')
    s = one(s, '''    if (downloading) {
        fill(renderer,103,964,1715,15,bg);''',
            '''    if (downloading || completed_visible) {
        fill(renderer,103,964,1715,15,bg);''')
    s = one(s, '''        std::string velocity="Tốc độ: Đang tính...";''',
            '''        if(completed_visible) {
            orbisshelf::draw_text(renderer,723,1002,3,"100% – Đã lưu PKG vào /data/pkg",gold);
        } else {
        std::string velocity="Tốc độ: Đang tính...";''')
    s = one(s, '''        orbisshelf::draw_text(renderer,1235,1002,3,fit_text(remaining,3,565),gold);
    } else if''',
            '''        orbisshelf::draw_text(renderer,1235,1002,3,fit_text(remaining,3,565),gold);
        }
    } else if''')
    # Consume one button-down per X press. Prevent repeated KEYDOWN/controller button
    # events from restarting a new download as soon as job_running becomes false.
    s = one(s, '''    int selected = 0;''', '''    int selected = 0;
    bool chepgame_x_down=false,chepgame_enter_down=false;''')
    s = one(s, '''            if (choose && count && !busy) start_job(state, JobInstall, &chosen);''',
            '''            if(event.type==SDL_JOYBUTTONUP && event.jbutton.button==0) chepgame_x_down=false;
            if(event.type==SDL_KEYUP && event.key.keysym.sym==SDLK_RETURN) chepgame_enter_down=false;
            bool chepgame_download_click=false;
            if(choose && event.type==SDL_JOYBUTTONDOWN) {
                chepgame_download_click=!chepgame_x_down;
                chepgame_x_down=true;
            } else if(choose && event.type==SDL_KEYDOWN) {
                chepgame_download_click=!chepgame_enter_down;
                chepgame_enter_down=true;
            }
            if (chepgame_download_click && count && !busy) start_job(state, JobInstall, &chosen);''')
    s = one(s,'BY SUPER MANH  v0.42','BY SUPER MANH  v0.43')
    s = one(s, '    if(type==JobInstall) {\n        const std::string existing=',
            '    if(type==JobInstall) {\n        chepgame_download_log("CHECK",0,item.size_bytes);\n        const std::string existing=')
    s = one(s, '        if(lstat(existing.c_str(),&existing_stat)==0) {',
            '        if(lstat(existing.c_str(),&existing_stat)==0) {\n            chepgame_download_log("EXISTS",(uint64_t)std::max((off_t)0,existing_stat.st_size),item.size_bytes);')
    s = one(s, '    if (!http.download(item.pkg_url, staged_path.c_str(), progress_callback, state, downloaded, error, token, item.size_bytes, item.sha256)) {',
            '    if (!http.download(item.pkg_url, staged_path.c_str(), progress_callback, state, downloaded, error, token, item.size_bytes, item.sha256)) {\n        chepgame_download_log("HTTP_FAIL",downloaded,item.size_bytes);')
    s = one(s, '    if (item.size_bytes && downloaded != item.size_bytes) {',
            '    chepgame_download_log("HTTP_COMPLETE",downloaded,item.size_bytes);\n    if (item.size_bytes && downloaded != item.size_bytes) {')
    s = one(s, '    std::remove((staged_path+".resume").c_str());\n    set_status(state, "Tải hoàn tất – PKG sẵn sàng tại /data/pkg", false);',
            '    std::remove((staged_path+".resume").c_str());\n    chepgame_download_log("READY",downloaded,item.size_bytes);\n    set_status(state, "Tải hoàn tất – PKG sẵn sàng tại /data/pkg", false);')
    s = one(s, '    bool download_finished = false;',
            '    bool download_finished = false;\n    bool download_verifying = false;')
    s = one(s, '    state->download_finished = false;\n    state->expected_size = item.size_bytes;',
            '    state->download_finished = false;\n    state->download_verifying = false;\n    state->expected_size = item.size_bytes;')
    s = one(s, '    state->download_active=false;\n        state->expected_size=0;',
            '    state->download_active=false;\n        state->download_verifying=false;\n        state->expected_size=0;')
    s = one(s, '        state->download_active = false;\n        pthread_mutex_unlock(&state->mutex);\n        set_status(state, "Đang kiểm tra tệp", true);',
            '        state->download_active = false;\n        state->download_verifying = true;\n        pthread_mutex_unlock(&state->mutex);\n        set_status(state, "Đang kiểm tra tệp", true);')
    s = one(s, 'downloading=false,completed_visible=false;',
            'downloading=false,completed_visible=false,verifying_visible=false;')
    s = one(s, '    completed_visible=state.download_finished;',
            '    completed_visible=state.download_finished;\n    verifying_visible=state.download_verifying;')
    s = one(s, '    } else if (total && (downloading || completed_visible)) {',
            '    } else if (total && (downloading || completed_visible || verifying_visible)) {')
    s = one(s, '    if (downloading || completed_visible) {',
            '    if (downloading || completed_visible || verifying_visible) {')
    s = one(s, '        if(completed_visible) {\n            orbisshelf::draw_text(renderer,723,1002,3,"100% – Đã lưu PKG vào /data/pkg",gold);\n        } else {',
            '        if(completed_visible || verifying_visible) {\n            orbisshelf::draw_text(renderer,723,1002,3,\n                verifying_visible?"100% – Đang kiểm tra SHA-256...":"100% – Đã lưu PKG vào /data/pkg",gold);\n        } else {')
    main.write_text(s, encoding='utf-8')
    mk = source / 'Makefile'
    mk.write_text(one(mk.read_text(encoding='utf-8'),'VERSION     := 0.42','VERSION     := 0.43'),encoding='utf-8')
    with (source / 'CHEPGAME_INFO.txt').open('a',encoding='utf-8') as f:
        f.write('v0.4.3: no repeated X events; strict HTTP byte count; '
                'completed progress retained; no re-download of existing PKG; preserve staging on verification failures.\n')
