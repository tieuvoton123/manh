# Add isolated BGFT remote install after layout patch. Never modify X download mode.
from pathlib import Path
import shutil

def rep(source, before, after, n=1):
    found=source.count(before)
    if found!=n:raise RuntimeError(f'BGFT patch mismatch {found} expected {n}: {before[:85]}')
    return source.replace(before,after,n)

def apply(source:Path, root:Path):
    main=source/'src/main.cpp'
    s=main.read_text(encoding='utf-8')
    s=rep(s,'#include <vector>', '#include <vector>\n#include <set>') if '#include <vector>' in s else s
    s=rep(s,'enum JobType { JobRefresh, JobInstall };',
        'enum JobType { JobRefresh, JobInstall, JobRemoteInstall };')
    s=rep(s,'    bool download_active = false;',
        '    bool download_active = false;\n    std::set<std::string> remote_submitted_ids;\n    int32_t last_remote_task_id = -1;')
    # This branch deliberately goes first: remote BGFT must not initialize HttpClient or
    # download anything to the HDD. Non-remote code remains bit-for-bit identical.
    start='''    orbisshelf::HttpClient http;
    std::string error;'''
    remote='''    // R1: direct PC URL -> PS4 BGFT. X-only local download is unchanged.
    if (type == JobRemoteInstall) {
        pthread_mutex_lock(&state->mutex);
        const bool duplicate = state->remote_submitted_ids.count(item.id) != 0;
        pthread_mutex_unlock(&state->mutex);
        if (duplicate) {
            set_status(state, "Đã gửi tác vụ cho game này. Xem Tải xuống trên PS4", false);
            return 0;
        }
        set_status(state, "Đang gửi tác vụ tải và cài...", true);
        std::string install_error;
        int32_t install_code = 0, bgft_task_id = -1;
        const bool accepted = chepgame::submit_remote_install(item.pkg_url, item.name,
                                         bgft_task_id, install_error, install_code);
        if (!accepted) {
            set_status(state, "Không thể tải và cài: " + install_error + " (nhấn X để chỉ tải)",
                       false, install_code);
            return 0;
        }
        pthread_mutex_lock(&state->mutex);
        state->remote_submitted_ids.insert(item.id);
        state->last_remote_task_id = bgft_task_id;
        pthread_mutex_unlock(&state->mutex);
        std::ostringstream message;
        message << "BGFT đã nhận tác vụ #" << bgft_task_id << ". Xem Tải xuống trên PS4";
        set_status(state, message.str(), false);
        return 0;
    }

    orbisshelf::HttpClient http;
    std::string error;'''
    s=rep(s,start,remote)
    s=rep(s,'state.status = type == JobRefresh ? "Đang kết nối máy chủ" : "Chuẩn bị tải";',
        'state.status = type == JobRefresh ? "Đang kết nối máy chủ" :\n'
        '                  (type == JobRemoteInstall ? "Đang chuẩn bị tải và cài" : "Chuẩn bị tải");')
    s=rep(s,'bool up = false, down = false, choose = false, refresh = false, quit = false, edit_url = false;',
        'bool up = false, down = false, choose = false, refresh = false, quit = false, edit_url = false, remote_install = false;')
    s=rep(s,'edit_url = event.key.keysym.sym == SDLK_u;',
        'edit_url = event.key.keysym.sym == SDLK_u;\n                remote_install = event.key.keysym.sym == SDLK_i;')
    s=rep(s,'edit_url = event.jbutton.button == 2;',
        'edit_url = event.jbutton.button == 2;\n                remote_install = event.jbutton.button == 5; // R1')
    s=rep(s,'            if (choose && count && !busy) start_job(state, JobInstall, &chosen);',
        '            if (choose && count && !busy) start_job(state, JobInstall, &chosen);\n'
        '            if (remote_install && count && !busy) start_job(state, JobRemoteInstall, &chosen);')
    # Header positions are anchored to text width and draw only on two rows;
    # do not squeeze a fifth label into the older button row.
    s=rep(s,'    orbisshelf::draw_text(renderer,77,90,2,"BY SUPER MANH  v0.37.3",muted);',
        '    orbisshelf::draw_text(renderer,77,90,2,"BY SUPER MANH  v0.38",muted);')
    s=rep(s,'    orbisshelf::draw_text(renderer,965,62,4,"X Tải",white);',
        '    orbisshelf::draw_text(renderer,890,62,4,"X Tải",white);')
    s=rep(s,'    orbisshelf::draw_text(renderer,1150,62,4,"△ Làm mới",white);',
        '    orbisshelf::draw_text(renderer,1335,62,3,"△ Làm mới",white);')
    s=rep(s,'    orbisshelf::draw_text(renderer,1410,62,4,"□ Máy chủ",white);',
        '    orbisshelf::draw_text(renderer,1550,62,3,"□ Máy chủ",white);')
    s=rep(s,'    orbisshelf::draw_text(renderer,1645,62,4,"O Thoát",white);',
        '    orbisshelf::draw_text(renderer,1742,62,2,"O Thoát",white);')
    # Dedicated highlighted R1 label in second row of header. Sits above the list.
    s=rep(s,'    // Library header and true columns:',
        '    orbisshelf::draw_text(renderer,1045,18,3,"R1  Tải và cài (BGFT)",gold);\n'
        '    // Library header and true columns:')
    main.write_text(s,encoding='utf-8')
    install=source/'src/chepgame_direct_install.cpp'
    install.write_text((root/'chepgame_direct_install.cpp').read_text(encoding='utf-8'),encoding='utf-8')
    (source/'src/chepgame_direct_install.hpp').write_text(
        (root/'chepgame_direct_install.hpp').read_text(encoding='utf-8'),encoding='utf-8')
    mk=source/'Makefile'
    m=mk.read_text(encoding='utf-8')
    m=rep(m,'VERSION     := 0.37','VERSION     := 0.38')
    mk.write_text(m,encoding='utf-8')
    info=source/'CHEPGAME_INFO.txt'
    info.write_text(info.read_text(encoding='utf-8')+
      'v0.3.8: X chi tai /data/pkg (unchanged). R1 BGFT remote install (experimental); no local duplication.\n',encoding='utf-8')
