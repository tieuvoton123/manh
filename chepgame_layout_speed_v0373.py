"""Last source-generation pass: measured-width minimalist PS4 layout and download meter."""
from pathlib import Path
import shutil


def require_replace(src: str, old: str, new: str, expected: int = 1) -> str:
    n = src.count(old)
    if n != expected:
        raise RuntimeError(f'v0.3.7.3 upstream fragment changed (want {expected}, saw {n}): {old[:110]}')
    return src.replace(old, new)


def apply(source: Path, bundle_root: Path) -> None:
    destination = source / 'src' / 'chepgame_transfer_meter.hpp'
    shutil.copyfile(bundle_root / 'chepgame_transfer_meter.hpp', destination)
    path = source / 'src' / 'main.cpp'
    s = path.read_text(encoding='utf-8')
    s = require_replace(s, '#include "chepgame_url_ui.hpp"',
                        '#include "chepgame_url_ui.hpp"\n#include "chepgame_transfer_meter.hpp"')
    s = require_replace(s, '#include "chepgame_transfer_meter.hpp"', '#include "chepgame_transfer_meter.hpp"\n#include <cmath>')
    s = require_replace(s, '    int32_t last_error_code;\n',
                        '    int32_t last_error_code;\n'
                        '    chepgame::TransferMeter meter;\n'
                        '    bool download_active = false;\n'
                        '    uint64_t expected_size = 0;\n')
    s = require_replace(s,
                        '    if (!running) { state->current = 0; state->total = 0; }',
                        '    if (!running) {\n'
                        '        state->current = state->total = 0;\n'
                        '        state->download_active = false;\n'
                        '        state->expected_size = 0;\n'
                        '        state->meter.reset();\n'
                        '    }')
    s = require_replace(s,
                        '    state->current = current;\n    state->total = total;',
                        '    state->current = current;\n'
                        '    state->total = total ? total : state->expected_size;\n'
                        '    if (state->download_active) state->meter.update(current, SDL_GetTicks());')
    s = require_replace(s,
                        '    const std::string staged_path = pkg_path + ".downloading";',
                        '    const std::string staged_path = pkg_path + ".downloading";')  # stable anchor
    s = require_replace(s,
                        '    uint64_t downloaded = 0;\n    const std::string token = optional_hf_token();',
                        '    pthread_mutex_lock(&state->mutex);\n'
                        '    state->download_active = true;\n'
                        '    state->expected_size = item.size_bytes;\n'
                        '    state->current = 0;\n'
                        '    state->total = item.size_bytes;\n'
                        '    state->meter.reset();\n'
                        '    pthread_mutex_unlock(&state->mutex);\n'
                        '    uint64_t downloaded = 0;\n'
                        '    const std::string token = optional_hf_token();')
    # Once all bytes are downloaded, prevent speed/ETA being displayed during checksum verification.
    s = require_replace(s,
                        '    if (!item.sha256.empty()) {\n        set_status(state, "Đang kiểm tra tệp", true);',
                        '    if (!item.sha256.empty()) {\n'
                        '        pthread_mutex_lock(&state->mutex);\n'
                        '        state->download_active = false;\n'
                        '        pthread_mutex_unlock(&state->mutex);\n'
                        '        set_status(state, "Đang kiểm tra tệp", true);')
    begin = s.index('void render(SDL_Renderer* renderer, SharedState& state, int selected) {')
    end = s.index('\n}\n\n} // namespace', begin)+2
    render = r'''// The atlas uses proportional glyph advances, so cap strings by rendered pixels.
std::string fit_text(const std::string& value, int scale, int max_pixels) {
    if (max_pixels <= 0) return "";
    if (orbisshelf::text_width(scale,value) <= max_pixels) return value;
    const std::string dots="...";
    const int available=max_pixels-orbisshelf::text_width(scale,dots);
    if (available<=0) return "";
    size_t pos=0;size_t end=0;
    while (pos < value.size()) {
        const unsigned char c=(unsigned char)value[pos];
        size_t len=1;
        if ((c&0xE0)==0xC0) len=2;
        else if ((c&0xF0)==0xE0) len=3;
        else if ((c&0xF8)==0xF0) len=4;
        if(pos+len>value.size())break;
        const std::string candidate=value.substr(0,pos+len);
        if(orbisshelf::text_width(scale,candidate)>available)break;
        pos+=len;end=pos;
    }
    return value.substr(0,end)+dots;
}
void draw_right(SDL_Renderer* r,int right,int y,int scale,const std::string& value,SDL_Color color) {
    orbisshelf::draw_text(r,right-orbisshelf::text_width(scale,value),y,scale,value,color);
}
void render(SDL_Renderer* renderer, SharedState& state, int selected) {
    const SDL_Color bg={22,12,15,255};
    const SDL_Color panel={45,24,27,255};
    const SDL_Color header={67,25,27,255};
    const SDL_Color selected_bg={132,49,39,255};
    const SDL_Color gold={255,215,77,255};
    const SDL_Color white={255,249,236,255};
    const SDL_Color muted={222,193,174,255};

    std::vector<CatalogItem> items;
    std::string status;
    uint64_t current=0,total=0;
    int32_t code=0;
    bool prompt=false,submitted=false,failed=false,busy=false,downloading=false;
    bool measured=false,stalled=false;
    double bytes_per_second=0.0;
    const uint32_t now=SDL_GetTicks();
    pthread_mutex_lock(&state.mutex);
    items=state.items;status=state.status;
    current=state.current;total=state.total;
    code=state.last_error_code;
    prompt=state.install_prompt;
    submitted=state.install_submitted;
    failed=state.install_failed;
    busy=state.job_running;
    downloading=state.download_active;
    measured=state.meter.has_estimate();
    stalled=state.meter.stalled(now);
    bytes_per_second=state.meter.speed(now);
    pthread_mutex_unlock(&state.mutex);

    // Header: brand on left, control legend on right. No temperature/FPS overlays.
    fill(renderer,0,0,kWidth,kHeight,bg);
    fill(renderer,0,0,kWidth,126,header);
    fill(renderer,0,123,kWidth,3,gold);
    orbisshelf::draw_text(renderer,75,17,7,"CHEPGAME.NET",gold);
    orbisshelf::draw_text(renderer,77,90,2,"BY SUPER MANH  v0.37.3",muted);
    // Four distinct navigation anchors prevent text clusters from touching.
    orbisshelf::draw_text(renderer,965,62,4,"X Tải",white);
    orbisshelf::draw_text(renderer,1150,62,4,"△ Làm mới",white);
    orbisshelf::draw_text(renderer,1410,62,4,"□ Máy chủ",white);
    orbisshelf::draw_text(renderer,1645,62,4,"O Thoát",white);

    // Library header and true columns: name x=100..1320, version x=1425,
    // size right-aligned to x=1810. Long titles never overlap metadata.
    orbisshelf::draw_text(renderer,83,151,4,"Thư viện",gold);
    std::ostringstream count;count<<items.size()<<" ứng dụng";
    draw_right(renderer,1820,165,3,count.str(),muted);
    if (items.empty()) {
        orbisshelf::draw_text(renderer,122,339,5,"Chưa có ứng dụng",white);
        orbisshelf::draw_text(renderer,126,416,3,"Kiểm tra máy chủ hoặc nhấn △ để làm mới",muted);
    } else {
        const int visible=9;
        int first=std::max(0,selected-visible+1);
        for (int row=0; row<visible && first+row<(int)items.size(); ++row) {
            const int index=first+row;
            const int y=220+row*74;
            fill(renderer,70,y,1780,64,index==selected?selected_bg:panel);
            if (index==selected)fill(renderer,70,y,7,64,gold);
            orbisshelf::draw_text(renderer,100,y+15,4,fit_text(items[index].name,4,1220),white);
            orbisshelf::draw_text(renderer,1420,y+19,3,
                 fit_text("v"+items[index].version,3,175),index==selected?gold:muted);
            const std::string size=human_bytes(items[index].size_bytes);
            draw_right(renderer,1815,y+19,3,fit_text(size,3,170),index==selected?gold:muted);
        }
    }

    // 175px footer: status; progress; separate cells for size, speed, ETA.
    fill(renderer,0,900,kWidth,180,header);
    fill(renderer,72,918,6,133,gold);
    orbisshelf::draw_text(renderer,100,916,3,fit_text(status,3,1440),white);
    if (code) {
        std::ostringstream err;err<<"Lỗi 0x";
        err.setf(std::ios::hex,std::ios::basefield);
        err.width(8);err.fill('0');err<<(uint32_t)code;
        draw_right(renderer,1824,916,3,err.str(),gold);
    } else if (total && downloading) {
        const unsigned int pct=(unsigned int)std::min(100.0,100.0*(double)current/(double)total);
        std::ostringstream p;p<<pct<<"%";
        draw_right(renderer,1824,916,3,p.str(),gold);
    }

    if (downloading) {
        fill(renderer,103,964,1715,15,bg);
        if (total>0) {
            const int done=(int)std::min(1715.0,1715.0*(double)current/(double)total);
            if (done>0)fill(renderer,103,964,done,15,gold);
        }
        const std::string amount="Đã tải: "+human_bytes(current)+
            (total>0?" / "+human_bytes(total):"");
        orbisshelf::draw_text(renderer,102,1002,3,fit_text(amount,3,540),white);
        std::string velocity="Tốc độ: Đang tính...";
        std::string remaining="Còn lại: Đang tính...";
        if (stalled && current>0) {
            velocity="Tốc độ: 0 KB/s";
            remaining="Còn lại: Đang chờ dữ liệu";
        } else if (measured) {
            velocity="Tốc độ: "+human_bytes((uint64_t)(bytes_per_second+0.5))+"/s";
            if (!total) remaining="Còn lại: Không xác định";
            else if (bytes_per_second>=1.0)
                remaining="Còn lại: "+chepgame::duration_vi(
                    chepgame::TransferMeter::seconds_remaining(current,total,bytes_per_second));
            else remaining="Còn lại: Đang tính...";
        }
        if (!total) remaining="Còn lại: Không xác định";
        orbisshelf::draw_text(renderer,723,1002,3,fit_text(velocity,3,420),white);
        orbisshelf::draw_text(renderer,1235,1002,3,fit_text(remaining,3,565),gold);
    } else if (busy) {
        orbisshelf::draw_text(renderer,102,1001,3,"Đang xử lý...",muted);
    } else {
        orbisshelf::draw_text(renderer,102,1001,3,"Kho lưu PKG: /data/pkg",muted);
    }

    if (prompt) {
        // Modal actions stay unchanged; never claim an unverified install succeeded.
        fill(renderer,259,255,1402,558,bg);
        fill(renderer,259,255,1402,7,gold);
        fill(renderer,274,273,1372,521,panel);
        const std::string title=submitted?"ĐÃ GỬI LỆNH CÀI":(failed?"CHƯA CÀI ĐƯỢC":"TẢI HOÀN TẤT");
        orbisshelf::draw_text(renderer,355,312,6,fit_text(title,6,1120),gold);
        orbisshelf::draw_text(renderer,358,400,3,
            submitted?"Xem tiến trình trên PS4":(failed?"Có thể cài qua GoldHEN":"Đã lưu PKG vào /data/pkg"),white);
        if (!submitted) {
            fill(renderer,337,498,1242,88,selected_bg);
            fill(renderer,337,498,7,88,gold);
            orbisshelf::draw_text(renderer,388,520,5,busy?"Đang xử lý...":"X  CÀI NGAY",gold);
        }
        orbisshelf::draw_text(renderer,365,643,3,"□  Về PS4 để cài bằng GoldHEN",white);
        orbisshelf::draw_text(renderer,365,696,3,"O  Quay lại",muted);
    }
}'''
    s = s[:begin] + render + s[end:]
    # Make latest visible version explicit without disrupting PS4 package identity.
    path.write_text(s, encoding='utf-8')
    info=source/'CHEPGAME_INFO.txt'
    info.write_text(info.read_text(encoding='utf-8') +
        'v0.3.7.3: layout 3 cot, footer tach hang, toc do tai, ETA (EWMA), file luu /data/pkg.\n',encoding='utf-8')
