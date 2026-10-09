"""Three isolated UI workflows: HDD BGFT, remote BGFT, Bato-inspired download-then-install.
The third is an original workflow; it does not contain GameBaTo code or a jailbreak.
"""
from pathlib import Path
import shutil


def change(s, old, new, n=1):
    actual=s.count(old)
    if actual != n:
        raise RuntimeError(f'THREE_MODES patch mismatch: expected {n}, got {actual}: {old[:125]!r}')
    return s.replace(old,new,n)


def apply(source:Path,root:Path):
    src=source/'src'
    path=src/'main.cpp'
    s=path.read_text(encoding='utf-8')
    # No changes to X, downloader, SHA256, or transfer meter for normal mode.
    s=change(s,'enum JobType { JobRefresh, JobInstall, JobRemoteInstall };',
        'enum JobType { JobRefresh, JobInstall, JobRemoteInstall, JobBatoInstall };')
    s=change(s,'    int32_t last_remote_task_id = -1;', '''    int32_t last_remote_task_id = -1;
    std::string tab_status[3];
    int32_t tab_error[3] = {0,0,0};
    int32_t tab_task_id[3] = {-1,-1,-1};
    bool last_status_plain = true;
    int active_job_tab = -1;''')
    # A complete worker result belongs to the mode that initiated it.
    s=change(s,'''    state->last_error_code = error_code;
''','''    state->last_error_code = error_code;
    if (!running && state->active_job_tab >= 0 && state->active_job_tab < 3) {
        const int tab=state->active_job_tab;
        state->tab_status[tab]=status;
        state->tab_error[tab]=error_code;
        state->active_job_tab=-1;
        state->last_status_plain=false;
    } else if (!running) {
        state->last_status_plain=true;
    }
''')
    s=change(s,'''    state.job_running=true;
    state.install_failed=false;
    state.status="Đang gửi lệnh cài...";''','''    state.job_running=true;
    state.install_failed=false;
    state.tab_status[0]="Đang gửi yêu cầu BGFT từ HDD";
    state.tab_error[0]=0;
    state.last_status_plain=false;
    state.status="Đang gửi lệnh cài...";''')
    s=change(s,'''    state->status=ok?"Đã gửi lệnh cài. Theo dõi trên PS4.":("Không thể cài ngay: "+error);''','''    state->status=ok?("BGFT HDD #"+std::to_string(task_id)+" đã nhận, chưa cài xong."):("BGFT HDD lỗi: "+error);
    state->tab_status[0]=state->status;
    state->tab_error[0]=code;
    state->last_status_plain=false;
    state->tab_task_id[0]=ok?task_id:-1;''')
    # Keep each tab's diagnostic log separate, so one BGFT error is not confused with another.
    s=change(s,'void* local_install_worker(void* p) {',r'''void chepgame_mode_log(int tab,const char* phase,int32_t code) {
    const char* names[3]={
        "/data/ChepGameStore/mode1_bgft_hdd.log",
        "/data/ChepGameStore/mode2_bgft_url.log",
        "/data/ChepGameStore/mode3_bato_style.log"};
    if(tab<0 || tab>2)return;
    FILE* f=std::fopen(names[tab],"a");
    if(!f)return;
    std::fprintf(f,"%s : 0x%08X\n",phase,(unsigned)code);
    std::fclose(f);
}
void* local_install_worker(void* p) {''')
    s=change(s,'''    std::string error; int32_t code=0;
    const bool ok=chepgame::submit_local_install(path,error,code);''','''    std::string error; int32_t code=0,task_id=-1;
    const bool ok=chepgame::submit_local_install_tracked(path,task_id,error,code);
    chepgame_mode_log(0,ok?"HDD_TASK_ACCEPTED":"HDD_TASK_REJECTED",code);
    if(ok)chepgame_mode_log(0,"BGFT_TASK_ID",task_id);''')
    helper=r'''void* chepgame_bato_install_stage(SharedState* state, const std::string& pkg_path, const CatalogItem& item) {
    // Bato-style is *our* 2-stage pipeline; downloaded bytes are verified by
    // the existing X path, then handed to BGFT from /data/pkg.
    // It is NOT reverse-engineered GameBaTo privileged code.
    pthread_mutex_lock(&state->mutex);
    state->install_prompt=false;
    state->tab_status[2]="Đã kiểm tra PKG, đang gửi BGFT để cài";
    pthread_mutex_unlock(&state->mutex);
    // Existing PKGs must also match the catalog; never auto-install an unchecked file.
    struct stat st;
    if(stat(pkg_path.c_str(),&st)!=0 || !S_ISREG(st.st_mode) || st.st_size<=0 ||
       (item.size_bytes && (uint64_t)st.st_size!=item.size_bytes)) {
        chepgame_mode_log(2,"FILE_NOT_VERIFIED",-2);
        set_status(state,"Bato-style: Tệp PKG không đúng dung lượng",false,-2);
        return nullptr;
    }
    if(!item.sha256.empty()) {
        std::string digest,validation_error;
        if(!orbisshelf::sha256_file(pkg_path.c_str(),digest,validation_error) || digest!=item.sha256) {
            chepgame_mode_log(2,"SHA256_NOT_VERIFIED",-3);
            set_status(state,"Bato-style: SHA-256 PKG không khớp",false,-3);
            return nullptr;
        }
    }
    std::string err;
    int32_t code=0,task=-1;
    const bool accepted=chepgame::submit_local_install_tracked(pkg_path,task,err,code);
    chepgame_mode_log(2,accepted?"BATO_TASK_ACCEPTED":"BATO_BGFT_REJECTED",code);
    if(accepted)chepgame_mode_log(2,"BGFT_TASK_ID",task);
    pthread_mutex_lock(&state->mutex);
    state->tab_task_id[2]=accepted?task:-1;
    state->tab_status[2]=accepted?("Bato-style: BGFT #"+std::to_string(task)+" đã nhận"):("Bato-style: bộ cài PS4 từ chối: "+err);
    state->tab_error[2]=code;
    state->install_prompt=false; // Never show X local install modal for Bato-style.
    pthread_mutex_unlock(&state->mutex);
    set_status(state, accepted?"Bato-style: Đã gửi lệnh cài, CHƯA xác minh hoàn tất":("Bato-style lỗi cài: "+err),false,code);
    return nullptr;
}

'''
    # Insert at beginning of job_main as a separate helper; 'type' is in job_main.
    anchor='void* job_main('
    if s.count(anchor)!=1: raise RuntimeError('job_main not found')
    s=s.replace(anchor,'void chepgame_mode_log(int tab,const char* phase,int32_t code);\n'+helper+anchor,1)
    # If a complete file exists, Bato-style installs it immediately rather than overwriting.
    s=change(s,'''        set_status(state, "PKG đã tải trước đó", false);''','''        if (type==JobBatoInstall) return chepgame_bato_install_stage(state,pkg_path,item);
        set_status(state, "PKG đã tải trước đó", false);''')
    # Post-download path is the original SHA+rename-verification; change only Bato follow-up.
    s=change(s,'''    set_status(state, "Tải hoàn tất", false);''','''    if (type==JobBatoInstall) return chepgame_bato_install_stage(state,pkg_path,item);
    set_status(state, "Tải hoàn tất", false);''')
    # BGFT URL is independent from HDD and Bato-style attempts.
    s=change(s,'''        if (!accepted) {
            set_status(state, "Không thể tải và cài: " + install_error + " (nhấn X để chỉ tải)",''','''        chepgame_mode_log(1,accepted?"URL_TASK_ACCEPTED":"URL_TASK_REJECTED",install_code);
        if (!accepted) {
            set_status(state, "Không thể tải và cài: " + install_error + " (nhấn X để chỉ tải)",''')
    s=change(s,'''        state->last_remote_task_id = bgft_task_id;''','''        state->last_remote_task_id = bgft_task_id;
        state->tab_task_id[1]=bgft_task_id;''')
    s=change(s,'''        state->remote_submitted_ids.insert(item.id);''','''        chepgame_mode_log(1,"BGFT_TASK_ID",bgft_task_id);
        state->remote_submitted_ids.insert(item.id);''')
    # Launch only one worker at a time, but keep three independent recorded outcomes.
    s=change(s,'''    state.status = type == JobRefresh ? "Đang kết nối máy chủ" :
                  (type == JobRemoteInstall ? "Đang chuẩn bị tải và cài" : "Chuẩn bị tải");''','''    state.status = type == JobRefresh ? "Đang kết nối máy chủ" :
                  (type == JobRemoteInstall ? "BGFT URL: Đang chuẩn bị" :
                  (type == JobBatoInstall ? "Bato-style: Đang chuẩn bị tải" : "Chuẩn bị tải"));
    state.active_job_tab=type == JobRemoteInstall ? 1 : (type == JobBatoInstall ? 2 : -1);
    state.last_status_plain=(state.active_job_tab<0);
    if(state.active_job_tab>=0) {
        state.tab_status[state.active_job_tab]=state.status;
        state.tab_error[state.active_job_tab]=0;
    }''')
    # Synchronized header UI: 3 tabs in the already-reserved library header area.
    s=change(s,'''void render(SDL_Renderer* renderer, SharedState& state, int selected) {''','''static int chepgame_active_tab=0;
void render(SDL_Renderer* renderer, SharedState& state, int selected) {''')
    s=change(s,'''    int32_t bgft_error=0;''','''    int32_t bgft_error=0;''') if False else s
    s=change(s,'''    bool measured=false,stalled=false;''','''    bool measured=false,stalled=false;
    bool plain_operation=true;
    std::string tab_note;
    int32_t tab_code=0;''')
    s=change(s,'''    code=state.last_error_code;''','''    code=state.last_error_code;
    plain_operation=state.last_status_plain;
    tab_note=state.tab_status[chepgame_active_tab];
    tab_code=state.tab_error[chepgame_active_tab];''')
    s=change(s,'''    // Library header and true columns:''','''    // Three distinct mode tabs; use D-pad LEFT/RIGHT to change, R1 to start.
    const char* tab_names[3]={"1 HDD BGFT","2 URL BGFT","3 Bato-style"};
    for(int k=0;k<3;++k) {
        const int tx=80+k*595;
        fill(renderer,tx,138,575,62,k==chepgame_active_tab?selected_bg:panel);
        if(k==chepgame_active_tab)fill(renderer,tx,194,575,5,gold);
        orbisshelf::draw_text(renderer,tx+19,152,4,tab_names[k],k==chepgame_active_tab?gold:white);
    }
    // Library header and true columns:''')
    s=change(s,'''    orbisshelf::draw_text(renderer,83,151,4,"Thư viện",gold);''','''    orbisshelf::draw_text(renderer,83,205,2,"Thư viện   ← → Đổi tab     R1 Chạy tab     X Chỉ tải về HDD",muted);''')
    # Footer display active tab error without replacing X download live details.
    s=change(s,'''    orbisshelf::draw_text(renderer,100,916,3,fit_text(status,3,1440),white);''','''    const std::string shown=(!busy && !plain_operation)?
        (tab_note.empty()?"Chưa chạy tab này. Chọn game rồi nhấn R1":tab_note):status;
    orbisshelf::draw_text(renderer,100,916,3,fit_text(shown,3,1440),white);''')
    s=change(s,'''    if (code) {
        std::ostringstream err;''','''    if (!busy && !plain_operation) code=tab_code;
    if (code) {
        std::ostringstream err;''')
    # BGFT URL mode's progress is shown only when tab 2 (index 1) is active.
    s=change(s,'    } else if (bgft_id>=0) {',
             '    } else if (chepgame_active_tab==1 && bgft_id>=0) {')
    # Input navigation on Dpad (keyboard and JOYHAT). R1 still triggers active mode.
    s=change(s,'''            bool up = false, down = false, choose = false, refresh = false, quit = false, edit_url = false, remote_install = false;''','''            bool up = false, down = false, left_tab = false, right_tab = false, choose = false, refresh = false, quit = false, edit_url = false, remote_install = false;''')
    s=change(s,'''                remote_install = event.key.keysym.sym == SDLK_i;''','''                remote_install = event.key.keysym.sym == SDLK_i;
                left_tab = event.key.keysym.sym == SDLK_LEFT;
                right_tab = event.key.keysym.sym == SDLK_RIGHT;''')
    s=change(s,'''                remote_install = event.jbutton.button == 5; // R1''','''                remote_install = event.jbutton.button == 5; // R1: action in active tab''')
    # SDL joystick hats for typical PS4 Dpad
    if '                down = (event.jhat.value & SDL_HAT_DOWN) != 0;' in s:
        s=change(s,'''                down = (event.jhat.value & SDL_HAT_DOWN) != 0;''','''                down = (event.jhat.value & SDL_HAT_DOWN) != 0;
                left_tab = (event.jhat.value & SDL_HAT_LEFT) != 0;
                right_tab = (event.jhat.value & SDL_HAT_RIGHT) != 0;''')
    s=change(s,'''            if (up && count) selected = (selected + count - 1) % count;''','''            if (left_tab && !busy) chepgame_active_tab=(chepgame_active_tab+2)%3;
            if (right_tab && !busy) chepgame_active_tab=(chepgame_active_tab+1)%3;
            if (up && count) selected = (selected + count - 1) % count;''')
    s=change(s,'''            if (remote_install && count && !busy) start_job(state, JobRemoteInstall, &chosen);''','''            if (remote_install && count && !busy) {
                if(chepgame_active_tab==0) {
                    // Mode 1: no network. Only use a fully existing .pkg on disk.
                    const std::string local=std::string(kDownloadDirectory)+"/"+chosen.id+"-"+chosen.version+".pkg";
                    struct stat st;
                    if(stat(local.c_str(),&st)==0 && S_ISREG(st.st_mode) && st.st_size>0) {
                        pthread_mutex_lock(&state.mutex);
                        state.ready_pkg_path=local;
                        state.install_prompt=true;
                        state.install_submitted=false;
                        state.tab_status[0]="BGFT HDD: Đang gửi tác vụ";
                        pthread_mutex_unlock(&state.mutex);
                        start_local_install_job(state);
                    } else {
                        pthread_mutex_lock(&state.mutex);
                        state.tab_status[0]="Không có PKG đã tải: bấm X trước";
                        state.tab_error[0]=-1;
                        state.last_status_plain=false;
                        pthread_mutex_unlock(&state.mutex);
                    }
                } else if(chepgame_active_tab==1) {
                    start_job(state,JobRemoteInstall,&chosen);
                } else {
                    start_job(state,JobBatoInstall,&chosen);
                }
            }''')
    s=change(s,'const int visible=9;','const int visible=8;')
    s=change(s,'const int y=220+row*74;','const int y=250+row*74;')
    # Version, makefile and a pinned independent release identifier.
    s=change(s,'R1  Tải và cài (BGFT)','R1  Chạy tab đã chọn')
    s=change(s,'BY SUPER MANH  v0.39.2','BY SUPER MANH  v0.40')
    path.write_text(s,encoding='utf-8')
    mk=source/'Makefile'
    m=mk.read_text(encoding='utf-8')
    m=change(m,'VERSION     := 0.392','VERSION     := 0.40')
    mk.write_text(m,encoding='utf-8')
    (src/'chepgame_direct_install.cpp').write_text((root/'chepgame_direct_install.cpp').read_text(encoding='utf-8'),encoding='utf-8')
    (src/'chepgame_direct_install.hpp').write_text((root/'chepgame_direct_install.hpp').read_text(encoding='utf-8'),encoding='utf-8')
    (source/'CHEPGAME_INFO.txt').write_text((source/'CHEPGAME_INFO.txt').read_text(encoding='utf-8') +
       '\nv0.4.0: 3 tabs independent UI/modes (BGFT HDD, BGFT URL, Bato-style app download+BGFT). No GameBaTo proprietary code.\n',encoding='utf-8')
