# PS4 BGFT only test v0.3.9.2: poll task progress and isolate init errors.
from pathlib import Path


def rep(s,old,new,n=1):
    count=s.count(old)
    if count!=n:raise RuntimeError(f'BGFT 0392 patch mismatch {count} != {n}: {old[:110]}')
    return s.replace(old,new,n)


def apply(source:Path,root:Path):
    main=source/'src/main.cpp'
    s=main.read_text(encoding='utf-8')
    s=rep(s,'    int32_t last_remote_task_id = -1;', '''    int32_t last_remote_task_id = -1;
    bool bgft_probe_ok = false;
    uint32_t bgft_probe_bytes=0, bgft_probe_total=0, bgft_probe_seconds=0;
    int32_t bgft_probe_error=0;''')
    s=rep(s,'        state->last_remote_task_id = bgft_task_id;', '''        state->last_remote_task_id = bgft_task_id;
        state->bgft_probe_ok=false;
        state->bgft_probe_error=0;
        state->bgft_probe_bytes=state->bgft_probe_total=state->bgft_probe_seconds=0;''')
    s=rep(s,'    bool measured=false,stalled=false;', '''    bool measured=false,stalled=false;
    int32_t bgft_id=-1,bgft_error=0;
    bool bgft_ok=false;
    uint32_t bgft_bytes=0,bgft_total=0,bgft_seconds=0;''')
    s=rep(s,'    code=state.last_error_code;', '''    code=state.last_error_code;
    bgft_id=state.last_remote_task_id;
    bgft_error=state.bgft_probe_error;
    bgft_ok=state.bgft_probe_ok;
    bgft_bytes=state.bgft_probe_bytes;
    bgft_total=state.bgft_probe_total;
    bgft_seconds=state.bgft_probe_seconds;''')
    s=rep(s,'''    } else if (busy) {
        orbisshelf::draw_text(renderer,102,1001,3,"Đang xử lý...",muted);
    } else {
        orbisshelf::draw_text(renderer,102,1001,3,"Kho lưu PKG: /data/pkg",muted);
    }''','''    } else if (bgft_id>=0) {
        if (bgft_ok && bgft_total>0) {
            fill(renderer,103,964,1715,15,bg);
            const int done=(int)std::min(1715.0,1715.0*(double)bgft_bytes/(double)bgft_total);
            if(done>0)fill(renderer,103,964,done,15,gold);
        }
        std::ostringstream info;
        info<<"BGFT #"<<bgft_id<<": ";
        if(bgft_error!=0) {
            info<<"Lỗi 0x"<<std::hex<<(uint32_t)bgft_error<<" (xem cai_dat.log)";
        } else if(!bgft_ok) {
            info<<"Đang đợi dữ liệu từ PS4...";
        } else if(bgft_total>0) {
            const int pct=(int)std::min(100.0,100.0*(double)bgft_bytes/(double)bgft_total);
            info<<pct<<"% dữ liệu  |  PS4 báo còn: ";
            if(bgft_seconds==0 || bgft_seconds>604800u)info<<"Đang tính...";
            else info<<chepgame::duration_vi(bgft_seconds);
        } else {
            info<<"Đang chạy trên PS4 (chưa có dung lượng)";
        }
        orbisshelf::draw_text(renderer,102,1001,3,fit_text(info.str(),3,1700),gold);
    } else if (busy) {
        orbisshelf::draw_text(renderer,102,1001,3,"Đang xử lý...",muted);
    } else {
        orbisshelf::draw_text(renderer,102,1001,3,"Kho lưu PKG: /data/pkg",muted);
    }''')
    anchor='''        if (url_screen) url_editor.draw(renderer);'''
    poll=r'''        // Only query the task on the SDL main thread every ~1.5 seconds.
        // BGFT continues in PS4 OS if Store exits. Never poll 60 times/second.
        static uint32_t last_bgft_poll_ms=0;
        const uint32_t bgft_now_ms=SDL_GetTicks();
        int32_t bgft_poll_id=-1;
        pthread_mutex_lock(&state.mutex);
        bgft_poll_id=state.last_remote_task_id;
        pthread_mutex_unlock(&state.mutex);
        if(bgft_poll_id>=0 && (uint32_t)(bgft_now_ms-last_bgft_poll_ms)>=1500u) {
            last_bgft_poll_ms=bgft_now_ms;
            chepgame::RemoteProgress progress;
            std::string progress_error;
            int32_t progress_code=0;
            const bool got=chepgame::query_remote_progress(bgft_poll_id,progress,
                                                          progress_error,progress_code);
            pthread_mutex_lock(&state.mutex);
            if(state.last_remote_task_id==bgft_poll_id) {
                state.bgft_probe_ok=got;
                state.bgft_probe_error=progress_code;
                if(got) {
                    state.bgft_probe_bytes=progress.transferred;
                    state.bgft_probe_total=progress.total;
                    state.bgft_probe_seconds=progress.rest_seconds;
                }
            }
            pthread_mutex_unlock(&state.mutex);
        }
'''
    # Insert BEFORE the if/else pair, never between `if (...)` and `else render`.
    # The previous position generated an illegal dangling-else C++ statement.
    s=rep(s,anchor,poll+anchor)
    s=rep(s,'BY SUPER MANH  v0.39.1','BY SUPER MANH  v0.39.2')
    main.write_text(s,encoding='utf-8')
    mk=source/'Makefile';m=mk.read_text(encoding='utf-8')
    m=rep(m,'VERSION     := 0.391','VERSION     := 0.392')
    mk.write_text(m,encoding='utf-8')
    (source/'src/chepgame_direct_install.cpp').write_text(
        (root/'chepgame_direct_install.cpp').read_text(encoding='utf-8'),encoding='utf-8')
    (source/'src/chepgame_direct_install.hpp').write_text(
        (root/'chepgame_direct_install.hpp').read_text(encoding='utf-8'),encoding='utf-8')
    info=source/'CHEPGAME_INFO.txt'
    info.write_text(info.read_text(encoding='utf-8')+
       'v0.3.9.2: BGFT-only diagnostic, no privilege payload, background progress from real BGFT, X download untouched.\n',encoding='utf-8')
