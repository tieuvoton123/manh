"""v0.4.2 downloader-first release: HTTP Range resume with overlap validation.

Preserves old X URL/downloading/rename behavior. Runs after all previous source passes.
"""
from pathlib import Path
import shutil
import re


def replace_one(s, old, new):
    if s.count(old) != 1:
        raise RuntimeError('Fast downloader source anchor mismatch: '+repr(old[:130]))
    return s.replace(old,new,1)


def apply(source:Path,root:Path):
    h=source/'src/http_client.hpp'
    cpp=source/'src/http_client.cpp'
    if h.is_file():
        s=h.read_text(encoding='utf-8')
        s=replace_one(s,'const std::string& bearer_token = std::string());\n\nprivate:',
                      'const std::string& bearer_token = std::string(),\n'
                      '                  uint64_t expected_size = 0, const std::string& expected_sha = std::string());\n\nprivate:')
        h.write_text(s,encoding='utf-8')
    if cpp.is_file() and 'bool HttpClient::download(' in cpp.read_text(encoding='utf-8'):
        apply_http(cpp,source,root)
    main=source/'src/main.cpp'
    s=main.read_text(encoding='utf-8')
    s=replace_one(s,
        'http.download(item.pkg_url, staged_path.c_str(), progress_callback, state, downloaded, error, token)',
        'http.download(item.pkg_url, staged_path.c_str(), progress_callback, state, downloaded, error, token, item.size_bytes, item.sha256)')
    # A downloaded PKG must never become visible in GoldHEN unless header sanity checks pass.
    marker='    // Another process (FTP) may have added the file while downloading.'
    s=replace_one(s,marker,'''    // Validate PS4 PKG header before promoting .downloading to visible .pkg.
    // This catches HTML error pages and non-PKG content with a matching size.
    {
        FILE* pkg_header=std::fopen(staged_path.c_str(),"rb");
        unsigned char magic[4]={0};
        const bool valid=pkg_header && std::fread(magic,1,4,pkg_header)==4 &&
            magic[0]==0x7f && magic[1]=='C' && magic[2]=='N' && magic[3]=='T';
        if(pkg_header)std::fclose(pkg_header);
        if(!valid) {
            std::remove(staged_path.c_str());
            std::remove((staged_path+".resume").c_str());
            set_status(state,"Tệp tải về không phải PS4 PKG hợp lệ",false);
            return 0;
        }
    }
'''+marker)
    s=replace_one(s,'''    set_status(state, "Tải hoàn tất", false);''',
                     '''    std::remove((staged_path+".resume").c_str());
    set_status(state, "Tải hoàn tất – PKG sẵn sàng tại /data/pkg", false);''')
    # No install popup after standard download; separate Installer app handles installs.
    s=replace_one(s,'''    state->install_prompt=true;
    state->install_failed=false;
    state->install_submitted=false;
    state->ready_pkg_path=pkg_path;
    pthread_mutex_unlock(&state->mutex);
    if (type==JobBatoInstall)''',
                     '''    state->install_prompt=false;
    state->install_failed=false;
    state->install_submitted=false;
    state->ready_pkg_path=pkg_path;
    pthread_mutex_unlock(&state->mutex);
    if (type==JobBatoInstall)''')
    # For already-downloaded file, do not show an install popup.
    s=replace_one(s,'''        state->ready_pkg_path=pkg_path;
        state->install_prompt=true;''',
                     '''        state->ready_pkg_path=pkg_path;
        state->install_prompt=false;''')
    # Disable R1 / three experimental install modes in downloader, leave unrelated source unchanged.
    s=replace_one(s,'if (remote_install && count && !busy) {','if (false && remote_install && count && !busy) {')
    # Hide mode tabs and replace with clear download-focused legend.
    old=r'''    orbisshelf::draw_text(renderer,1045,18,3,"R1  Chạy tab đã chọn",gold);
    // Three distinct mode tabs; use D-pad LEFT/RIGHT to change, R1 to start.
    const char* tab_names[3]={"1 HDD BGFT","2 URL BGFT","3 Bato-style"};
    for(int k=0;k<3;++k) {
        const int tx=80+k*595;
        fill(renderer,tx,138,575,62,k==chepgame_active_tab?selected_bg:panel);
        if(k==chepgame_active_tab)fill(renderer,tx,194,575,5,gold);
        orbisshelf::draw_text(renderer,tx+19,152,4,tab_names[k],k==chepgame_active_tab?gold:white);
    }'''
    new=r'''    orbisshelf::draw_text(renderer,1045,18,3,"CHỈ TẢI PKG · /data/pkg",gold);'''
    s=replace_one(s,old,new)
    s=replace_one(s,
        '''orbisshelf::draw_text(renderer,83,205,2,"Thư viện   ← → Đổi tab     R1 Chạy tab     X Chỉ tải về HDD",muted);''',
        '''orbisshelf::draw_text(renderer,83,205,3,"Thư viện – X Tải PKG     △ Làm mới     □ Máy chủ",muted);''')
    s=replace_one(s,'BY SUPER MANH  v0.41','BY SUPER MANH  v0.42')
    # Category + version share the metadata column; size retains own column.
    s=replace_one(s,
        'orbisshelf::draw_text(renderer,1420,y+19,3,\n                 fit_text("v"+items[index].version,3,175),index==selected?gold:muted);',
        'orbisshelf::draw_text(renderer,1350,y+19,3,\n                 fit_text(items[index].type+" · v"+items[index].version,3,290),index==selected?gold:muted);')
    # This app uses a full-HD software renderer. ~30 FPS reduces CPU/memory
    # pressure while a separate worker moves large PKG data over the network.
    if '        SDL_Delay(16);' in s:
        s=replace_one(s,'        SDL_Delay(16);','        SDL_Delay(33);')
    main.write_text(s,encoding='utf-8')
    mk=source/'Makefile'
    m=mk.read_text(encoding='utf-8')
    m=replace_one(m,'VERSION     := 0.41','VERSION     := 0.42')
    mk.write_text(m,encoding='utf-8')
    with (source/'CHEPGAME_INFO.txt').open('a',encoding='utf-8') as f:
        f.write('v0.4.2: download-only UI, auto-retry and overlap-verified resumable Range, '
                '1MiB buffer, no install popup. PS4 PKG magic checked before final rename.\n')


def apply_http(cpp:Path,source:Path,root:Path):
    s=cpp.read_text(encoding='utf-8')
    s=replace_one(s,'#include "http_client.hpp"', '#include "http_client.hpp"\n#include "chepgame_resume_policy.hpp"\n#include <orbis/libkernel.h>\n#include <sys/stat.h>')
    s=replace_one(s,
        'const std::string& bearer_token,\n              RequestHandles& handles',
        'const std::string& bearer_token, const std::string& range,\n              RequestHandles& handles')
    s=replace_one(s,
        '    const int send_result = sceHttpSendRequest(handles.req, 0, 0);',
        '''    if (!range.empty()) {
        if(sceHttpAddRequestHeader(handles.req,"Range",range.c_str(),1)<0) {
            error="Range header rejected";return false;
        }
    }
    const int send_result = sceHttpSendRequest(handles.req, 0, 0);''')
    s=replace_one(s,
        'RequestHandles& handles, int32_t& status, std::string& final_url, std::string& error) {',
        'RequestHandles& handles, int32_t& status, std::string& final_url, std::string& error,\n'
        '                    const std::string& range = std::string()) {')
    s=replace_one(s,'open_get(http_context_, url, scoped_token, handles, status, location, error)',
                  'open_get(http_context_, url, scoped_token, range, handles, status, location, error)') if False else s
    s=replace_one(s,'open_get(http_context, url, scoped_token, handles, status, location, error)',
                  'open_get(http_context, url, scoped_token, range, handles, status, location, error)')
    start=s.index('bool HttpClient::download(')
    tail=s.index('\n} // namespace orbisshelf',start)
    fn=r'''bool HttpClient::download(const std::string& url, const char* destination, ProgressCallback callback,
                          void* user, uint64_t& downloaded_bytes, std::string& error,
                          const std::string& bearer_token, uint64_t expected_size,
                          const std::string& expected_sha) {
    // Local staging and a tightly scoped identity protect against resuming a different PKG.
    const std::string metadata_path=std::string(destination)+".resume";
    const std::string identity=chepgame::resume_identity(url,expected_size,expected_sha);
    bool same=false;
    {
        FILE* meta=std::fopen(metadata_path.c_str(),"rb");
        if(meta) {
            std::vector<char> stored(identity.size()+1,0);
            const size_t n=std::fread(&stored[0],1,stored.size(),meta);
            same=(n==identity.size() && std::memcmp(&stored[0],identity.data(),n)==0);
            std::fclose(meta);
        }
    }
    struct stat st;
    // Reject symlinks/devices in shared /data/pkg; never follow them during staging.
    if(lstat(destination,&st)==0 && !S_ISREG(st.st_mode)) {
        error="Tệp tạm không an toàn (không phải file thường)";return false;
    }
    if(lstat(metadata_path.c_str(),&st)==0 && !S_ISREG(st.st_mode)) {
        error="Metadata tải không an toàn";return false;
    }
    uint64_t completed=0;
    if(same && stat(destination,&st)==0 && S_ISREG(st.st_mode) && st.st_size>=0 &&
       (!expected_size || (uint64_t)st.st_size<=expected_size)) completed=(uint64_t)st.st_size;
    else {
        // Reset only our own .downloading staging file, never an existing .pkg.
        FILE* cleared=std::fopen(destination,"wb");
        if(!cleared){error="Không thể tạo tệp tải";return false;}
        std::fclose(cleared);
        FILE* meta=std::fopen(metadata_path.c_str(),"wb");
        if(!meta){error="Không thể lưu thông tin tiếp tục tải";return false;}
        const bool valid=std::fwrite(identity.data(),1,identity.size(),meta)==identity.size();
        const int close_status=std::fclose(meta);
        if(!valid||close_status!=0){error="Không lưu được thông tin tải";return false;}
    }
    downloaded_bytes=completed;
    if(callback)callback(completed,expected_size,user);
    if(expected_size && completed==expected_size) return true; // Caller verifies PKG/SHA.

    std::vector<unsigned char> buffer(1024*1024);
    for(int attempt=0;attempt<=chepgame::kMaxRetries;++attempt) {
        const bool resume=completed>0;
        const uint64_t request_start=resume?chepgame::overlap_from(completed):0;
        const std::string range=resume?("bytes="+std::to_string(request_start)+"-"):std::string();
        RequestHandles handles;
        int32_t status=0; std::string final_url;
        bool opened=open_final_get(http_context_,url,bearer_token,handles,status,final_url,error,range);
        if(!opened) {
            close_request(handles);
            if(attempt==chepgame::kMaxRetries) return false;
            sceKernelUsleep((uint32_t)(250000*(attempt+1)));
            continue;
        }
        char* response_headers=0;size_t response_header_size=0;
        std::string content_range;
        if(sceHttpGetAllResponseHeaders(handles.req,&response_headers,&response_header_size)>=0)
            header_value(response_headers,response_header_size,"content-range",content_range);
        uint64_t server_total=0;
        if(!chepgame::range_valid(status,resume,request_start,content_range,expected_size,server_total)) {
            close_request(handles);
            if(status==416 && resume) { // Range unsatisfiable, request fresh full copy.
                completed=0;
                FILE* restart=std::fopen(destination,"wb");if(restart)std::fclose(restart);
                continue;
            }
            error=status_error(status)+" / invalid Content-Range";
            return false;
        }
        if(expected_size==0 && server_total>0) expected_size=server_total;
        const bool server_ignored_range=resume && status==200;
        if(server_ignored_range) {
            completed=0; // Full 200 response: never append full response to a partial file.
        }
        std::vector<unsigned char> overlap;
        if(resume && status==206) {
            const size_t overlap_len=(size_t)(completed-request_start);
            overlap.resize(overlap_len);
            FILE* previous=std::fopen(destination,"rb");
            if(!previous || fseeko(previous,(off_t)request_start,SEEK_SET)!=0 ||
               std::fread(&overlap[0],1,overlap_len,previous)!=overlap_len) {
                if(previous)std::fclose(previous);
                close_request(handles);
                error="Không đọc được phần tệp để kiểm tra nối tải";
                return false;
            }
            std::fclose(previous);
        }
        FILE* file=std::fopen(destination,completed>0?"ab":"wb");
        if(!file){close_request(handles);error="Không mở được tệp PKG";return false;}
        std::vector<char> write_buffer(1024*1024);
        std::setvbuf(file,&write_buffer[0],_IOFBF,write_buffer.size());
        size_t overlap_checked=0;
        bool io_ok=true,match=true;
        for(;;) {
            const int count=sceHttpReadData(handles.req,&buffer[0],(uint32_t)buffer.size());
            if(count<0) {error="Kết nối tải bị ngắt";io_ok=false;break;}
            if(count==0)break;
            size_t consumed=0;
            if(overlap_checked<overlap.size()) {
                const size_t take=std::min((size_t)count,overlap.size()-overlap_checked);
                if(std::memcmp(&overlap[overlap_checked],&buffer[0],take)!=0) {
                    error="Tệp nguồn đã đổi; không ghép dữ liệu cũ";
                    match=false;break;
                }
                overlap_checked+=take;consumed=take;
            }
            const size_t usable=(size_t)count-consumed;
            if(expected_size && usable>expected_size-completed) {
                error="Máy chủ gửi quá dung lượng PKG";io_ok=false;break;
            }
            if(usable && std::fwrite(&buffer[consumed],1,usable,file)!=usable) {
                error="Không ghi được PKG vào HDD";io_ok=false;break;
            }
            completed+=usable;
            downloaded_bytes=completed;
            if(callback && usable)callback(completed,expected_size,user);
        }
        if(std::fclose(file)!=0) {
            error="Không lưu được PKG vào HDD";
            close_request(handles);
            return false; // Disk full / delayed flush failure; keep staging for FTP inspection.
        }
        // stdio is buffered: base retries on actual file length, not fwrite count.
        struct stat on_disk;
        if(stat(destination,&on_disk)!=0 || !S_ISREG(on_disk.st_mode) || on_disk.st_size<0) {
            close_request(handles);
            error="Không kiểm tra được file tạm";return false;
        }
        completed=(uint64_t)on_disk.st_size;
        downloaded_bytes=completed;
        close_request(handles);
        if(!match) {
            // A changed remote must never be spliced. Retry only as a clean download.
            FILE* reset=std::fopen(destination,"wb");
            if(!reset){error="Không thể làm mới tệp tải";return false;}
            std::fclose(reset);completed=downloaded_bytes=0;
            if(callback)callback(0,expected_size,user);
            continue;
        }
        if(overlap_checked!=overlap.size()) {error="Phản hồi Range bị thiếu dữ liệu đối chiếu";io_ok=false;}
        if(io_ok && (!expected_size || completed==expected_size)) {
            downloaded_bytes=completed;
            if(callback)callback(completed,expected_size,user);
            return true;
        }
        if(io_ok && expected_size && completed<expected_size)error="Tải chưa đủ; đang tiếp tục";
        if(attempt<chepgame::kMaxRetries)
            sceKernelUsleep((uint32_t)(250000*(attempt+1)));
    }
    return false; // Keep .downloading + .resume for the next session.
}
'''
    s=s[:start]+fn+s[tail:]
    cpp.write_text(s,encoding='utf-8')
    shutil.copyfile(root/'chepgame_resume_policy.hpp',source/'src/chepgame_resume_policy.hpp')
