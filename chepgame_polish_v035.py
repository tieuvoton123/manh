from pathlib import Path
import shutil

def one(s, before, after, n=1):
    actual=s.count(before)
    if actual!=n:raise RuntimeError('Không khớp nguồn: '+repr(before[:85])+' (found '+str(actual)+')')
    return s.replace(before,after,n)

def apply(source:Path, root:Path)->None:
    main=source/'src/main.cpp'
    s=main.read_text(encoding='utf-8')
    # Keep the app's original GoldHEN-compatible download-to-/data/pkg flow.
    if '#include "pkg_installer.hpp"' in s:
        s=one(s,'#include "pkg_installer.hpp"','#include "chepgame_direct_install.hpp"')
    else:
        s=one(s,'#include "catalog.hpp"','#include "catalog.hpp"\n#include "chepgame_direct_install.hpp"')
    s=one(s, '    bool install_prompt;\n',
          '    bool install_prompt;\n    bool install_submitted;\n    bool install_failed;\n    std::string ready_pkg_path;\n')
    s=one(s,'install_prompt(false) {','install_prompt(false), install_submitted(false), install_failed(false) {')
    # Record the verified local path, and surface an install action even for already-downloaded packages.
    already='''        set_status(state, "PKG đã có ở /data/pkg (không ghi đè)", false);'''
    s=one(s,already,'''        pthread_mutex_lock(&state->mutex);
        state->ready_pkg_path=pkg_path;
        state->install_prompt=true;
        state->install_failed=false;
        state->install_submitted=false;
        pthread_mutex_unlock(&state->mutex);
'''+already)
    ready='''    state->install_prompt=true;
    pthread_mutex_unlock(&state->mutex);
    set_status(state, "Tải xong. PKG đã ở /data/pkg", false);'''
    s=one(s,ready,'''    state->install_prompt=true;
    state->install_failed=false;
    state->install_submitted=false;
    state->ready_pkg_path=pkg_path;
    pthread_mutex_unlock(&state->mutex);
    set_status(state, "Tải xong. PKG đã ở /data/pkg", false);''')
    # Add a self-contained background worker: never run privileged PS4 calls in SDL's event thread.
    loc='''bool start_job(SharedState& state, JobType type, const CatalogItem* item) {'''
    worker=r'''void* local_install_worker(void* p) {
    SharedState* state=static_cast<SharedState*>(p);
    std::string path;
    pthread_mutex_lock(&state->mutex);
    path=state->ready_pkg_path;
    pthread_mutex_unlock(&state->mutex);
    std::string error; int32_t code=0;
    const bool ok=chepgame::submit_local_install(path,error,code);
    pthread_mutex_lock(&state->mutex);
    state->job_running=false;
    state->install_prompt=true;
    state->install_submitted=ok;
    state->install_failed=!ok;
    state->last_error_code=code;
    state->status=ok?"Đã gửi lệnh cài. Theo dõi trên PS4.":("Không thể cài ngay: "+error);
    pthread_mutex_unlock(&state->mutex);
    return nullptr;
}
bool start_local_install_job(SharedState& state) {
    pthread_mutex_lock(&state.mutex);
    if(state.job_running || !state.install_prompt || state.ready_pkg_path.empty() || state.install_submitted) {
        pthread_mutex_unlock(&state.mutex);
        return false;
    }
    state.job_running=true;
    state.install_failed=false;
    state.status="Đang gửi lệnh cài...";
    state.last_error_code=0;
    pthread_mutex_unlock(&state.mutex);
    pthread_t thread;
    if(pthread_create(&thread,nullptr,local_install_worker,&state)!=0) {
        pthread_mutex_lock(&state.mutex);
        state.job_running=false;
        state.install_failed=true;
        state.status="Không tạo được tác vụ cài";
        pthread_mutex_unlock(&state.mutex);
        return false;
    }
    pthread_detach(thread);
    return true;
}

'''
    s=one(s,loc,worker+loc)
    # Replace v0.3.4 prompt event branch with a real, explicit install request.
    start='''            if (prompt_ready && !busy) {
                if (choose) { running=false; continue; } // Exit to PS4 home screen.
                if (quit) {
                    pthread_mutex_lock(&state.mutex);
                    state.install_prompt=false;
                    pthread_mutex_unlock(&state.mutex);
                }
                continue;
            }
'''
    end='''            if (prompt_ready) {
                if (!busy && edit_url) { running=false; continue; } // GoldHEN menu fallback
                if (!busy && quit) {
                    pthread_mutex_lock(&state.mutex);
                    state.install_prompt=false;
                    pthread_mutex_unlock(&state.mutex);
                }
                if (!busy && choose) start_local_install_job(state);
                continue;
            }
'''
    s=one(s,start,end)
    # Remove all boilerplate from Store rendering (entire body, so no hidden old English).
    begin=s.index('void render(SDL_Renderer* renderer, SharedState& state, int selected) {')
    finish=s.index('\n}\n\n} // namespace',begin)+2
    rendered=r'''void render(SDL_Renderer* renderer, SharedState& state, int selected) {
    const SDL_Color bg={20,11,12,255};
    const SDL_Color panel={42,22,23,255};
    const SDL_Color head={64,19,21,255};
    const SDL_Color selected_bg={110,35,30,255};
    const SDL_Color primary={255,217,69,255};
    const SDL_Color fg={253,248,235,255};
    const SDL_Color subtle={222,185,158,255};
    std::vector<CatalogItem> items;
    std::string status;
    uint64_t progress=0,total=0;
    int32_t code=0;
    bool ready=false,submitted=false,failed=false,running=false;
    pthread_mutex_lock(&state.mutex);
    items=state.items;status=state.status;
    progress=state.current;total=state.total;
    code=state.last_error_code;
    ready=state.install_prompt;
    submitted=state.install_submitted;
    failed=state.install_failed;
    running=state.job_running;
    pthread_mutex_unlock(&state.mutex);

    fill(renderer,0,0,kWidth,kHeight,bg);
    fill(renderer,0,0,kWidth,125,head);
    fill(renderer,0,122,kWidth,3,primary);
    orbisshelf::draw_text(renderer,65,24,7,"CHEPGAME.NET",primary);
    orbisshelf::draw_text(renderer,66,88,2,"BY SUPER MANH   v0.35",subtle);
    orbisshelf::draw_text(renderer,1065,52,3,"X Tải   △ Làm mới   □ Máy chủ   O Thoát",fg);
    orbisshelf::draw_text(renderer,75,164,4,"Thư viện",primary);
    std::ostringstream cnt;cnt<<items.size()<<" ứng dụng";
    orbisshelf::draw_text(renderer,1550,170,3,cnt.str(),subtle);

    if(items.empty()) {
        orbisshelf::draw_text(renderer,140,353,5,"Chưa có ứng dụng",fg);
        orbisshelf::draw_text(renderer,142,435,3,"Kiểm tra mạng hoặc nhấn △ để làm mới",subtle);
    } else {
        const int visible=9;
        int first=std::max(0,selected-visible+1);
        for(int row=0;row<visible && first+row<(int)items.size();++row) {
            const int index=first+row;
            const int y=230+row*74;
            fill(renderer,69,y,1780,65,index==selected?selected_bg:panel);
            if(index==selected)fill(renderer,69,y,7,65,primary);
            orbisshelf::draw_text(renderer,101,y+17,4,truncate_text(items[index].name,47),fg);
            const std::string info=items[index].version+"  "+human_bytes(items[index].size_bytes);
            orbisshelf::draw_text(renderer,1440,y+20,3,truncate_text(info,25),index==selected?primary:subtle);
        }
    }
    fill(renderer,0,943,kWidth,137,head);
    orbisshelf::draw_text(renderer,80,962,3,truncate_text(status,65),fg);
    if(total || progress) {
        fill(renderer,80,1025,1710,15,bg);
        if(total) {
            const int w=(int)(progress*1710.0/total);
            fill(renderer,80,1025,std::max(1,std::min(w,1710)),15,primary);
            std::ostringstream pct; pct<<(int)(100.0*progress/total)<<"%";
            orbisshelf::draw_text(renderer,1720,978,3,pct.str(),primary);
        }
    }
    if(code) {
        std::ostringstream error;error<<"Mã lỗi: 0x";
        error.setf(std::ios::hex,std::ios::basefield);
        error.width(8); error.fill('0'); error<<(uint32_t)code;
        orbisshelf::draw_text(renderer,1315,1003,2,error.str(),primary);
    }

    if(ready) {
        fill(renderer,230,256,1460,578,bg);
        fill(renderer,230,256,1460,7,primary);
        fill(renderer,247,275,1426,535,panel);
        const std::string title=submitted?"ĐÃ GỬI LỆNH CÀI":(failed?"CHƯA CÀI ĐƯỢC":"TẢI HOÀN TẤT");
        orbisshelf::draw_text(renderer,347,325,6,title,primary);
        orbisshelf::draw_text(renderer,350,415,3,submitted?"Kiểm tra tiến trình cài trên PS4":
            (failed?"Có thể cài bằng GoldHEN":"Đã lưu PKG vào /data/pkg"),fg);
        if(!submitted) {
            fill(renderer,336,511,1250,83,selected_bg);
            fill(renderer,336,511,8,83,primary);
            orbisshelf::draw_text(renderer,376,536,5,running?"Đang xử lý...":"X  CÀI NGAY",primary);
        }
        orbisshelf::draw_text(renderer,357,656,3,"□  Về PS4 - cài bằng GoldHEN",fg);
        orbisshelf::draw_text(renderer,357,711,3,"O  Trở lại danh sách",subtle);
    }
}'''
    s=s[:begin]+rendered+s[finish:]
    # Keep only Vietnamese text in the connection UI and make the layout more compact.
    source.joinpath('src/chepgame_url_ui.cpp').write_text(
        (root/'chepgame_url_ui.cpp').read_text(encoding='utf-8')
          .replace('"Nhập địa chỉ JSON của kho ứng dụng"','"Địa chỉ máy chủ"')
          .replace('"X: Nhập    □: Xóa    L1/R1: Con trỏ"','"X Nhập    □ Xóa    L1/R1 Di chuyển"')
          .replace('"O  Bỏ qua"','"O  Dùng địa chỉ đã lưu"'),encoding='utf-8')
    s=s.replace('"PKG đã có ở /data/pkg (không ghi đè)"', '"PKG đã tải trước đó"')
    s=s.replace('"Tải xong. PKG đã ở /data/pkg"','"Tải hoàn tất"')
    s=s.replace('"Không tải được danh sách: " + error','"Lỗi tải danh sách: " + error')
    s=s.replace('"Danh sách JSON không hợp lệ: " + error','"Danh sách không hợp lệ: " + error')
    s=s.replace('"Không thể truy cập /data/pkg"','"Không thể lưu vào /data/pkg"')
    s=s.replace('"Đang kiểm tra SHA-256"','"Đang kiểm tra tệp"')
    main.write_text(s,encoding='utf-8')
    shutil.copyfile(root/'chepgame_direct_install.cpp', source/'src/chepgame_direct_install.cpp')
    shutil.copyfile(root/'chepgame_direct_install.hpp', source/'src/chepgame_direct_install.hpp')
    mk=source/'Makefile';content=mk.read_text(encoding='utf-8')
    content=one(content,'VERSION     := 0.34','VERSION     := 0.35')
    if '-lSceVideoOut' in content:
        content=one(content,'-lSceVideoOut','-lSceAppInstUtil -lSceBgft -lSceVideoOut')
    else:
        content=one(content,'-lSDL2','-lSceAppInstUtil -lSceBgft -lSDL2')
    mk.write_text(content,encoding='utf-8')
    info=source/'CHEPGAME_INFO.txt'
    info.write_text(info.read_text(encoding='utf-8')+'0.3.5: Việt hóa gọn, có thử cài trực tiếp BGFT, có dự phòng GoldHEN; KHÔNG dùng kernel jailbreak.\n',encoding='utf-8')
    # Guard: no obsolete branding and English controls in compiled UI source.
    for filename in ['main.cpp','chepgame_url_ui.cpp']:
        contents=(source/'src'/filename).read_text(encoding='utf-8')
        for bad in ['BRAND OK','DOWNLOAD+INSTALL','X DOWNLOAD','TRIANGLE REFRESH','NO ENABLED PACKAGES','X   VỀ PS4 ĐỂ CÀI']:
            if bad in contents:raise RuntimeError('Chuỗi chưa gỡ khỏi UI: '+bad+' in '+filename)
