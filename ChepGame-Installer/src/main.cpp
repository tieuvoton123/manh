#include "pkg_scan.hpp"
#include "installer.hpp"
#include "font.hpp"
#include "task_guard.hpp"
#include <SDL2/SDL.h>
#include <orbis/SystemService.h>
#include <orbis/Sysmodule.h>
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <sys/stat.h>

namespace {
const int W=1920,H=1080;
const char* const kPkgDir="/data/pkg";
const char* const kStoreDir="/data/ChepGameStore/downloads";
const char* const kLogDir="/data/ChepGameInstaller";
const char* const kPendingFile="/data/ChepGameInstaller/pending_task.txt";
const SDL_Color bg={23,10,14,255},panel={53,22,27,255},active={122,39,40,255};
const SDL_Color gold={255,215,91,255},white={242,237,226,255},muted={196,176,161,255};
void rect(SDL_Renderer* r,int x,int y,int w,int h,SDL_Color c){
    SDL_SetRenderDrawColor(r,c.r,c.g,c.b,c.a);SDL_Rect v={x,y,w,h};SDL_RenderFillRect(r,&v);
}
void label(SDL_Renderer* r,int x,int y,int size,const std::string& s,SDL_Color c=white){chepfont::draw(r,x,y,size,s,c);}
std::string error_hex(int32_t code){char b[24];std::snprintf(b,sizeof(b),"0x%08X",(unsigned)code);return b;}
void render(SDL_Renderer* r,const std::vector<chepinstaller::PackageFile>& files,int selected,
            bool confirm,bool ack_confirm,bool started,const std::string& status,const chepinstaller::InstallerResult& result,
            unsigned progress,bool progress_good) {
    rect(r,0,0,W,H,bg);
    rect(r,0,0,W,127,panel);
    label(r,68,28,46,"CHEPGAME.NET",gold);
    label(r,70,85,26,"VIET HOA SUPER MANH | CHEPGAME.NET | INSTALLER v0.3.3",muted);
    label(r,1190,43,26,"Quét HDD + Store downloads",white);
    label(r,72,148,34,"DANH SÁCH GAME ĐÃ TẢI",gold);
    label(r,1290,153,26,"Số PKG: "+std::to_string(files.size()),muted);
    const int visible=9;
    int begin=std::max(0,selected-visible+1);
    for(int k=0;k<visible && begin+k<(int)files.size();k++){
        const int ix=begin+k,y=207+k*75;
        rect(r,66,y,1788,66,ix==selected?active:panel);
        const std::string prefix=files[ix].full_path.compare(0,strlen(kStoreDir),kStoreDir)==0?"[STORE] ":"[PKG] ";
        const std::string name=chepfont::clip(prefix+files[ix].filename,34,1260);
        label(r,90,y+9,34,name,ix==selected?gold:white);
        const std::string bytes=chepinstaller::pretty_bytes(files[ix].size);
        label(r,1540,y+14,26,bytes,ix==selected?white:muted);
    }
    if(files.empty()){
        label(r,100,340,34,"Chưa có PKG hoàn chỉnh ở HDD hoặc Store",white);
        label(r,100,400,26,"Dùng ChepGame Store để tải trước, sau đó bấm nút Làm mới.",muted);
    }
    rect(r,0,901,W,179,panel);
    label(r,68,921,26,chepfont::clip(status,26,1750),gold);
    if(result.code!=0)label(r,1440,962,26,"Lỗi: "+error_hex(result.code),white);
    else if(started){
        label(r,68,962,26,"BGFT Task: "+std::to_string(result.task_id)+"  |  "+
            (progress_good?("Ước lượng "+std::to_string(progress)+"%"):("Theo dõi thông báo PS4")),white);
    }
    label(r,69,1030,26,"X Chọn/Cài     □ Làm mới     △ Xác nhận tác vụ trước     O Thoát",white);
    if(started) {
        label(r,68,993,23,"Tác vụ chờ kiểm tra. Vào PS4 Notifications/Downloads trước khi nhấn △.",gold);
    }
    if(ack_confirm) {
        rect(r,280,305,1350,380,{15,8,12,255});
        rect(r,300,325,1310,340,active);
        label(r,350,361,43,"ĐÃ KIỂM TRA TÁC VỤ TRÊN PS4?",gold);
        label(r,350,445,27,"X – Xóa cờ đang chờ để chọn PKG tiếp theo",white);
        label(r,350,510,27,"O – Quay lại. Không kết luận game đã cài xong.",white);
        label(r,350,575,25,"Chỉ xóa file ghi nhớ tác vụ, KHÔNG xóa PKG hay game.",gold);
    }
    if(confirm && selected>=0 && selected<(int)files.size()){
        rect(r,280,305,1350,380,{15,8,12,255});
        rect(r,300,325,1310,340,active);
        label(r,353,361,46,"XÁC NHẬN CÀI PKG",gold);
        label(r,355,446,34,chepfont::clip(files[selected].filename,34,1180),white);
        label(r,355,513,26,"X – Gửi tác vụ cài   |   O – Hủy",white);
        label(r,355,576,26,"Không tự xóa file hoặc gỡ game hiện có.",gold);
    }
}
}
int main(int,char**) {
    mkdir("/data/ChepGameInstaller",0777);
    // A normal scan is harmless. Only run third-party JBC when the user
    // explicitly presses the refresh button, or confirms an installation.
    const std::vector<std::string> locations={kPkgDir,kStoreDir};
    std::vector<chepinstaller::PackageFile> files;
    std::string error,status;
    const bool initial_scan=chepinstaller::scan_package_locations(locations,files,error);
    status=error.empty()?"Sẵn sàng – chọn game để cài trên PS4":error;
    if(!initial_scan)
        status+=" | Nhấn □ để thử JBC và quét lại";
    if(SDL_Init(SDL_INIT_VIDEO|SDL_INIT_JOYSTICK)!=0)return 1;
    SDL_Window* win=SDL_CreateWindow("ChepGame PKG Installer",SDL_WINDOWPOS_UNDEFINED,SDL_WINDOWPOS_UNDEFINED,W,H,0);
    if(!win){SDL_Quit();return 2;}
    SDL_Surface* surface=SDL_GetWindowSurface(win);
    SDL_Renderer* r=SDL_CreateSoftwareRenderer(surface);
    if(!r){SDL_DestroyWindow(win);SDL_Quit();return 3;}
    SDL_Joystick* joy=SDL_NumJoysticks()>0?SDL_JoystickOpen(0):nullptr;
    chepinstaller::InstallerResult result;
    bool running=true,confirm=false,ack_confirm=false,started=false,progress_good=false;
    int selected=0;unsigned progress=0;
    uint32_t last_poll=0;
    uint32_t last_confirm_press=0;
    bool progress_failed=false;
    bool can_poll=false;
    chepinstaller::PendingTask pending;
    struct stat previous_state;
    const bool journal_exists=lstat(kPendingFile,&previous_state)==0;
    if(chepinstaller::read_pending_task(kPendingFile,pending)) {
        started=true;
        result.accepted=true;result.task_id=pending.task_id;result.title_id=pending.title_id;
        result.step="PREVIOUS_TASK_NOT_VERIFIED";
        status="Có tác vụ từ lần mở trước: "+pending.filename+". Kiểm tra Downloads rồi nhấn △.";
        progress_failed=true; // Do not claim a resumed process has BGFT permissions.
    } else if(journal_exists) {
        // A corrupted journal must never silently allow duplicate task registration.
        started=true;progress_failed=true;
        result.step="PENDING_JOURNAL_INVALID";
        status="File lưu tác vụ lỗi. Kiểm tra Downloads, nhấn △ xác nhận để bỏ cờ.";
    }
    while(running){
        SDL_Event e;
        while(SDL_PollEvent(&e)){
            bool up=false,down=false,choose=false,cancel=false,refresh=false,ack=false;
            if(e.type==SDL_QUIT){running=false;continue;}
            if(e.type==SDL_KEYDOWN){
                up=e.key.keysym.sym==SDLK_UP;down=e.key.keysym.sym==SDLK_DOWN;
                choose=e.key.keysym.sym==SDLK_RETURN;cancel=e.key.keysym.sym==SDLK_ESCAPE;
                refresh=e.key.keysym.sym==SDLK_r;ack=e.key.keysym.sym==SDLK_t;
            }
            if(e.type==SDL_JOYHATMOTION){up=(e.jhat.value&SDL_HAT_UP)!=0;down=(e.jhat.value&SDL_HAT_DOWN)!=0;}
            if(e.type==SDL_JOYBUTTONDOWN){
                choose=e.jbutton.button==0;cancel=e.jbutton.button==1;refresh=e.jbutton.button==2;ack=e.jbutton.button==3;
            }
            // Ignore synthetic keyboard key repeat and rapid duplicate button events.
            if(e.type==SDL_KEYDOWN && e.key.repeat!=0)choose=false;
            if(choose){
                const uint32_t now=SDL_GetTicks();
                if(last_confirm_press && now-last_confirm_press<400)choose=false;
                else last_confirm_press=now;
            }
            if(ack_confirm){
                if(cancel){ack_confirm=false;status="Giữ nguyên cờ tác vụ đang chờ.";}
                else if(choose){
                    if(chepinstaller::acknowledge_pending_task(kPendingFile)){
                        ack_confirm=false;started=false;can_poll=false;progress_failed=false;
                        result=chepinstaller::InstallerResult();progress=0;progress_good=false;
                        status="Đã xóa cờ chờ (không xác minh cài xong). Có thể chọn PKG khác.";
                    }else{ack_confirm=false;status="Không xóa được cờ chờ, kiểm tra FTP/quyền ghi.";}
                }
                continue;
            }
            if(confirm){
                if(cancel){confirm=false;status="Đã hủy. PKG vẫn giữ nguyên.";}
                else if(choose){
                    confirm=false;
                    if(!chepinstaller::unchanged_package(files[selected])){
                        status="File PKG đã thay đổi sau khi quét. Bấm □ làm mới trước khi cài.";
                        continue;
                    }
                    result=chepinstaller::begin_install(files[selected].full_path);
                    started=result.accepted;can_poll=started;
                    progress_good=false;progress_failed=false;progress=0;
                    if(started){
                        pending.task_id=result.task_id;pending.title_id=result.title_id;
                        pending.filename=files[selected].filename;
                        if(chepinstaller::write_pending_task(kPendingFile,pending))
                            status="Đã gửi tác vụ cho PS4; chưa xác nhận cài xong. Kiểm tra Downloads.";
                        else status="Đã gửi tác vụ nhưng không lưu được cờ phiên! Kiểm tra log.";
                    }
                    else status="Cài không được: "+result.step+" ("+error_hex(result.code)+")";
                }
                continue;
            }
            if(cancel){running=false;continue;}
            if(ack && started){ack_confirm=true;continue;}
            if(refresh){
                // Explicit user action: attempt JBC for shared HDD access.
                const bool jbc=chepinstaller::enable_hdd_scan_access();
                const bool scan_ok=chepinstaller::scan_package_locations(locations,files,error);
                if(selected>=(int)files.size())selected=files.empty()?0:(int)files.size()-1;
                status=error.empty()?"Đã làm mới danh sách PKG.":error;
                if(!scan_ok)status+=" | Không đọc được HDD";
                if(!jbc)status+=" | JBC không sẵn sàng để cài";
            }
            if(up&&!files.empty())selected=(selected+(int)files.size()-1)%(int)files.size();
            if(down&&!files.empty())selected=(selected+1)%(int)files.size();
            if(choose&&!files.empty()){
                if(started)status="Đã có lệnh BGFT trong phiên này; xem Downloads trước khi cài tiếp.";
                else confirm=true;
            }
        }
        if(started && can_poll && !progress_failed && SDL_GetTicks()-last_poll>=1500){
            last_poll=SDL_GetTicks();int32_t err=0;
            progress_good=chepinstaller::get_progress(result.task_id,progress,err);
            if(err!=0){
                status="BGFT báo lỗi: "+error_hex(err)+". Xem thông báo hệ thống.";
                progress_good=false;progress_failed=true;
            }
        }
        render(r,files,selected,confirm,ack_confirm,started,status,result,progress,progress_good);
        SDL_UpdateWindowSurface(win);
        SDL_Delay(33); // 30 FPS software rendering: less CPU while BGFT works
    }
    // No detached workers: the system owns any already-accepted BGFT task.
    if(joy)SDL_JoystickClose(joy);
    chepfont::clear();SDL_DestroyRenderer(r);SDL_DestroyWindow(win);SDL_Quit();
    // PS4 Home exit service avoids returning through a suspended background SDL app.
    sceSysmoduleLoadModuleInternal(ORBIS_SYSMODULE_INTERNAL_SYSTEM_SERVICE);
    sceSystemServiceLoadExec("exit",nullptr);
    return 0;
}
