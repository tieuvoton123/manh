# v0.3.4 Vietnamese on-screen UX / GoldHEN handoff
from pathlib import Path
import re, shutil


def apply(source: Path, bundle_root: Path) -> None:
    main = source / 'src' / 'main.cpp'
    s=main.read_text(encoding='utf-8')
    s=s.replace('"CANNOT SAVE URL - CHECK STORAGE"', '"Không lưu được địa chỉ"')
    s=s.replace('"STARTING"', '"Sẵn sàng"')

    # Human-readable Vietnamese and technical status details.
    messages={
        '"NETWORK INIT FAILED: " + error':'"Lỗi kết nối mạng: " + error',
        '"REFRESHING CATALOG"':'"Đang tải danh sách"',
        '"CATALOG REFRESH FAILED: " + error':'"Không tải được danh sách: " + error',
        '"CATALOG INVALID: " + error':'"Danh sách JSON không hợp lệ: " + error',
        '"CATALOG UPDATED"':'"Đã cập nhật danh sách"',
        '"DOWNLOADING " + item.name':'"Đang tải: " + item.name',
        '"PKG ALREADY IN /DATA/PKG - NOT OVERWRITTEN"':'"PKG đã có ở /data/pkg (không ghi đè)"',
        '"CANNOT ACCESS /DATA/PKG - CHECK PERMISSIONS"':'"Không truy cập được /data/pkg"',
        '"DOWNLOAD FAILED: " + error':'"Tải thất bại: " + error',
        '"SIZE CHECK FAILED - NO PKG PUBLISHED"':'"Sai dung lượng. Đã hủy tệp tạm"',
        '"VERIFYING SHA256"':'"Đang kiểm tra SHA-256"',
        '"SHA256 CHECK FAILED - NO PKG PUBLISHED"':'"Sai mã SHA-256. Đã hủy tệp tạm"',
        '"PKG FILE ALREADY EXISTS - NOT OVERWRITTEN"':'"PKG đã có, không ghi đè"',
        '"FINALIZE PKG FAILED - CHECK /DATA/PKG"':'"Không thể hoàn tất tệp PKG"',
        '"PKG READY IN /DATA/PKG - OPEN GOLDHEN PACKAGE INSTALLER"':'"Tải xong. PKG đã ở /data/pkg"',
        '"STARTING CATALOG REFRESH"':'"Đang kết nối máy chủ"',
        '"STARTING DOWNLOAD"':'"Chuẩn bị tải"',
    }
    for a,b in messages.items():
        s=s.replace(a,b)

    # Clean, minimal brand, UTF-8-safe text shortening.
    start=s.index('std::string truncate_text(const std::string& value, size_t max_chars) {')
    end=s.index('\nvoid render(SDL_Renderer* renderer, SharedState& state, int selected) {',start)
    s=s[:start]+r'''std::string truncate_text(const std::string& value, size_t max_chars) {
    std::string out; size_t i=0, count=0;
    while (i<value.size() && count<max_chars) {
        const unsigned char c=(unsigned char)value[i];
        size_t n=1;
        if ((c&0xe0)==0xc0) n=2;
        else if ((c&0xf0)==0xe0) n=3;
        else if ((c&0xf8)==0xf0) n=4;
        if (i+n>value.size()) break;
        out.append(value,i,n); i+=n; ++count;
    }
    if (i<value.size()) out+="...";
    return out;
}
''' + s[end:]

    # Main Store layout. Keep data, progress and error code from upstream, restyled.
    start=s.index('void render(SDL_Renderer* renderer, SharedState& state, int selected) {')
    end=s.index('\n}\n\n} // namespace', start)+2
    draw=r'''void render(SDL_Renderer* renderer, SharedState& state, int selected) {
    const SDL_Color bg={25,10,13,255};
    const SDL_Color top={63,14,17,255};
    const SDL_Color panel={43,20,23,255};
    const SDL_Color hover={103,28,30,255};
    const SDL_Color text={255,248,226,255};
    const SDL_Color muted={225,184,154,255};
    const SDL_Color yellow={255,210,64,255};

    std::vector<CatalogItem> items;
    std::string status;
    uint64_t current=0, total=0;
    int32_t error_code=0;
    bool prompt=false;
    pthread_mutex_lock(&state.mutex);
    items=state.items; status=state.status;
    current=state.current; total=state.total;
    error_code=state.last_error_code;
    prompt=state.install_prompt;
    pthread_mutex_unlock(&state.mutex);

    fill(renderer,0,0,kWidth,kHeight,bg);
    fill(renderer,0,0,kWidth,138,top);
    fill(renderer,0,134,kWidth,4,yellow);
    orbisshelf::draw_text(renderer,74,22,8,"CHEPGAME.NET",yellow);
    orbisshelf::draw_text(renderer,79,99,3,"BY SUPER MANH",muted);
    orbisshelf::draw_text(renderer,1100,56,3,"X Tải  |  △ Cập nhật  |  □ URL  |  O Thoát",text);

    fill(renderer,64,165,1792,59,top);
    orbisshelf::draw_text(renderer,91,181,4,"KHO ỨNG DỤNG",yellow);
    std::ostringstream count; count << items.size() << " mục";
    orbisshelf::draw_text(renderer,1650,187,3,count.str(),muted);

    if (items.empty()) {
        orbisshelf::draw_text(renderer,134,371,6,"Chưa có ứng dụng",text);
        orbisshelf::draw_text(renderer,139,455,3,"Kiểm tra máy chủ hoặc nhấn △ để cập nhật",muted);
    } else {
        const int visible=9;
        int first=selected-visible+1;
        if(first<0) first=0;
        if(selected<first) first=selected;
        for(int row=0; row<visible && first+row<(int)items.size();++row) {
            const int index=first+row;
            const int y=238+row*75;
            fill(renderer,66,y,1788,66,index==selected?hover:panel);
            if(index==selected)fill(renderer,66,y,8,66,yellow);
            orbisshelf::draw_text(renderer,100,y+17,4,truncate_text(items[index].name,43),text);
            const std::string info="v"+items[index].version+"   "+human_bytes(items[index].size_bytes);
            orbisshelf::draw_text(renderer,1390,y+22,3,truncate_text(info,29),index==selected?yellow:muted);
        }
    }

    fill(renderer,0,939,kWidth,141,top);
    fill(renderer,73,954,9,97,yellow);
    orbisshelf::draw_text(renderer,109,964,3,truncate_text(status,68),text);
    if(error_code) {
        std::ostringstream code; code<<"Mã 0x";
        code.setf(std::ios::hex,std::ios::basefield);
        code.width(8);code.fill('0');code<<(uint32_t)error_code;
        orbisshelf::draw_text(renderer,1485,1002,2,code.str(),yellow);
    }
    if(current || total) {
        fill(renderer,104,1020,1700,14,bg);
        int amount=0;
        if(total) amount=(int)((double)current/(double)total*1700.0);
        fill(renderer,104,1020,std::max(2,std::min(amount,1700)),14,yellow);
        std::ostringstream done;
        if(total)done<<(int)((double)current/(double)total*100.0)<<"%";
        else done<<human_bytes(current);
        orbisshelf::draw_text(renderer,1680,977,3,done.str(),yellow);
    }

    if(prompt) {
        // A real menu handoff is unavailable; X exits to the PS4 home screen.
        fill(renderer,235,243,1450,588,bg);
        fill(renderer,235,243,1450,8,yellow);
        fill(renderer,252,260,1416,554,panel);
        orbisshelf::draw_text(renderer,367,325,7,"TẢI HOÀN TẤT",yellow);
        orbisshelf::draw_text(renderer,370,435,4,"PKG đã lưu tại /data/pkg/",text);
        fill(renderer,351,530,1220,93,hover);
        fill(renderer,351,530,9,93,yellow);
        orbisshelf::draw_text(renderer,407,558,5,"X   VỀ PS4 ĐỂ CÀI",yellow);
        orbisshelf::draw_text(renderer,369,661,3,"GoldHEN > Debug Settings > Package Source: HDD",muted);
        orbisshelf::draw_text(renderer,369,704,3,"Package Installer > chọn PKG",muted);
        orbisshelf::draw_text(renderer,369,766,3,"O   Tiếp tục xem kho",text);
    }
}'''
    s=s[:start]+draw+s[end:]

    # Add a safe post-download prompt: X returns to PS4 home, not an undocumented GoldHEN direct launch.
    s=s.replace('    int32_t last_error_code;\n', '    int32_t last_error_code;\n    bool install_prompt;\n',1)
    s=s.replace('last_error_code(0) {', 'last_error_code(0), install_prompt(false) {',1)
    needle='''    set_status(state, "Tải xong. PKG đã ở /data/pkg", false);'''
    if s.count(needle)!=1: raise RuntimeError('Không tìm thấy nhánh tải thành công')
    s=s.replace(needle, '''    pthread_mutex_lock(&state->mutex);
    state->install_prompt=true;
    pthread_mutex_unlock(&state->mutex);
    set_status(state, "Tải xong. PKG đã ở /data/pkg", false);''',1) if False else s
    # job_main uses SharedState* state (pointer); do not assume stack object.
    s=s.replace(needle, '''    pthread_mutex_lock(&state->mutex);
    state->install_prompt=true;
    pthread_mutex_unlock(&state->mutex);
    set_status(state, "Tải xong. PKG đã ở /data/pkg", false);''',1)

    anchor='''            if (up && count) selected = (selected + count - 1) % count;'''
    if s.count(anchor)!=1: raise RuntimeError('Không tìm thấy vòng điều khiển Store')
    s=s.replace(anchor,'''            bool prompt_ready=false;
            pthread_mutex_lock(&state.mutex);
            prompt_ready=state.install_prompt;
            pthread_mutex_unlock(&state.mutex);
            if (prompt_ready && !busy) {
                if (choose) { running=false; continue; } // Exit to PS4 home screen.
                if (quit) {
                    pthread_mutex_lock(&state.mutex);
                    state.install_prompt=false;
                    pthread_mutex_unlock(&state.mutex);
                }
                continue;
            }
'''+anchor,1)
    main.write_text(s,encoding='utf-8')

    # Runtime system TrueType engine handles Vietnamese diacritics
    # in all UI strings and downloaded metadata, not only the brand name.
    # System font replacement occurs in final v0.3.9 pass.

    # Localize low-level network error messages where present.
    client=source/'src/http_client.cpp'
    c=client.read_text(encoding='utf-8')
    diagnostics={
        'sceHttpCreateTemplate failed':'Không thể tạo yêu cầu HTTP',
        'sceHttpCreateConnectionWithURL failed':'Không thể kết nối URL',
        'sceHttpCreateRequestWithURL failed':'Không thể gửi yêu cầu',
        'sceHttpSendRequest failed':'Lỗi gửi HTTP',
        'sceHttpGetStatusCode failed':'Không nhận được phản hồi',
        'failed to add Authorization header':'Không thể xác thực',
        'redirect response did not contain Location':'Link chuyển hướng không hợp lệ',
        'refused non-HTTPS redirect':'Từ chối chuyển hướng không an toàn',
        'too many HTTP redirects':'Quá nhiều lần chuyển hướng',
        'HTTP request failed with status ':'Mã HTTP: ',
        'failed to load network system modules':'Không thể khởi tạo mạng',
        'sceNetPoolCreate failed':'Không thể tạo vùng nhớ mạng',
        'sceSslInit failed':'Không thể khởi tạo SSL',
        'sceHttpInit failed':'Không thể khởi tạo HTTP',
        'sceHttpReadData failed':'Lỗi đọc dữ liệu từ máy chủ',
        'HTTP response exceeded size limit':'Dữ liệu máy chủ quá lớn',
        'cannot create destination file':'Không thể tạo file tải',
        'failed to write downloaded PKG':'Không thể ghi file PKG',
        'failed to flush downloaded PKG':'Không thể lưu file PKG',
    }
    for a,b in diagnostics.items(): c=c.replace(a,b)
    client.write_text(c,encoding='utf-8')

    # Native JSON/catalog and checksum errors are user-visible too.
    for name, labels in {
        'catalog.cpp': {
            'missing string field: ': 'Thiếu trường: ',
            'field must be a string: ': 'Trường phải là chuỗi: ',
            'field must be a boolean: ': 'Trường phải là đúng/sai: ',
            'catalog root must be an object': 'Dữ liệu JSON không đúng cấu trúc',
            'unsupported schema_version': 'Phiên bản JSON chưa hỗ trợ',
            'items must be an array': 'Danh sách items phải là mảng',
            'catalog item must be an object': 'Mục trong danh sách không hợp lệ',
            'size_bytes must be a non-negative integer': 'Dung lượng PKG không hợp lệ',
            'item id/name/pkg_url is invalid': 'ID, tên hoặc link PKG không hợp lệ',
            'unsupported package type: ': 'Loại PKG chưa hỗ trợ: ',
            'sha256 must contain 64 hexadecimal characters': 'SHA-256 phải có 64 ký tự hex',
            'cannot open ': 'Không thể mở ',
            'cannot read ': 'Không thể đọc ',
        },
        'sha256.cpp': {
            'cannot open downloaded file for hashing': 'Không thể mở PKG để kiểm tra SHA-256',
            'failed while hashing downloaded file': 'Lỗi kiểm tra SHA-256',
        },
    }.items():
        filepath=source/'src'/name
        content=filepath.read_text(encoding='utf-8')
        for a,b in labels.items(): content=content.replace(a,b)
        filepath.write_text(content,encoding='utf-8')

    info=source/'CHEPGAME_INFO.txt'
    k=info.read_text(encoding='utf-8')
    info.write_text(k.replace('0.3.3','0.3.4')+'Giao diện tiếng Việt; X về PS4 để mở GoldHEN.\n',encoding='utf-8')
