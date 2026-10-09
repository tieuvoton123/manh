#include "chepgame_direct_install.hpp"
#include <orbis/AppInstUtil.h>
#include <orbis/Bgft.h>
#include <orbis/Sysmodule.h>
#include <orbis/UserService.h>
#include <orbis/libkernel.h>
#include <cstring>
#include <cstdlib>
#include <cstdio>
#include <sys/stat.h>
#include <mutex>

namespace chepgame {
namespace {
std::mutex installer_lock;
uint8_t* bgft_heap = nullptr;
bool bgft_ready = false;
bool app_ready = false;
// A failed BGFT initialization is terminal for this Store session. Never
// repeatedly call a failing system service from the R1 button.
bool bgft_attempted = false;
int32_t bgft_init_error = 0;
bool jbc_attempted = false;
bool jbc_ready = false;
bool app_load_attempted = false;
int32_t app_load_error = 0;
void diagnose(const char* step,int32_t code);

// JBC is optional and NOT bundled. A user-supplied legitimate build may be
// placed in app0/sce_module/libjbc.sprx when building the PKG.
// Only invoke it ONCE after a user explicitly selects an installation mode.
bool try_optional_jbc() {
    if (jbc_ready) return true;
    if (jbc_attempted) return false;
    jbc_attempted = true;
    struct stat st;
    const char* path="/app0/sce_module/libjbc.sprx";
    if (stat(path,&st)!=0 || !S_ISREG(st.st_mode)) {
        diagnose("JBC_NOT_BUNDLED",-1);
        return false;
    }
    int32_t handle=static_cast<int32_t>(sceKernelLoadStartModule(path,0,nullptr,0,nullptr,nullptr));
    diagnose("JBC_LOAD",handle);
    if (handle<=0) return false;
    typedef bool (*JailbreakFn)();
    JailbreakFn jailbreak=nullptr;
    int32_t ret=sceKernelDlsym(handle,"Jailbreak",reinterpret_cast<void**>(&jailbreak));
    diagnose("JBC_RESOLVE",ret);
    if(ret!=0 || !jailbreak)return false;
    // JBC may fail or crash on incompatible firmware. Never retry here.
    bool ok=jailbreak();
    diagnose("JBC_CALL",ok?0:-1);
    jbc_ready=ok;
    return ok;
}


int32_t load_module(const char* file, OrbisSysModuleInternal id) {
    // No kernel patches or bundled jailbreak payload: try existing GoldHEN privileges only.
    const int32_t direct = static_cast<int32_t>(sceSysmoduleLoadModuleInternal(id));
    if (direct >= 0) return 0;
    char path[256];
    std::snprintf(path,sizeof(path),"/system/common/lib/%s",file);
    int32_t result=static_cast<int32_t>(sceKernelLoadStartModule(path,0,nullptr,0,nullptr,nullptr));
    if (result >= 0) return 0;
    const char* word=sceKernelGetFsSandboxRandomWord();
    if (word && *word) {
        std::snprintf(path,sizeof(path),"/%s/common/lib/%s",word,file);
        result=static_cast<int32_t>(sceKernelLoadStartModule(path,0,nullptr,0,nullptr,nullptr));
        if (result >= 0) return 0;
    }
    return result;
}

void diagnose(const char* step,int32_t code) {
    FILE* fp=std::fopen("/data/ChepGameStore/cai_dat.log","a");
    if (!fp) return;
    std::fprintf(fp,"%s : 0x%08X\n",step,static_cast<unsigned>(code));
    std::fclose(fp);
}
bool failed(const char* label,int32_t result,std::string& error,int32_t& code) {
    if(result==0) return false;
    error=label; code=result; diagnose(label,result);return true;
}

// BGFT-only preflight for R1. Unlike HDD local install, remote tasks do not
// require us to load SysUtil, SystemService or AppInstUtil up front.
// Leave X/local install untouched so it remains an independent fallback.
bool ensure_remote_bgft(std::string& error,int32_t& code) {
    if(bgft_ready) return true;
    if(bgft_attempted) {
        code=bgft_init_error;
        error="BGFT đã lỗi khi khởi tạo; hãy mở lại Store sau khi xem log";
        return false;
    }
    // Keep the previous load order. A separately supplied JBC may permit
    // sandboxed code to reach privileged modules; never auto-run at startup.
    int32_t result=load_module("libSceBgft.sprx",ORBIS_SYSMODULE_INTERNAL_BGFT);
    diagnose("REMOTE_LOAD_BGFT",result);
    if(failed("Không nạp được BGFT",result,error,code))return false;
    // In the user's module probe, loading JBC succeeded on this firmware;
    // in the old Store it was absent. Opt-in only when packaged.
    try_optional_jbc();
    bgft_attempted=true;
    if(!bgft_heap) bgft_heap=static_cast<uint8_t*>(std::malloc(1024*1024));
    if(!bgft_heap) {
        error="Không đủ bộ nhớ BGFT";code=-1;
        bgft_init_error=code;
        diagnose("REMOTE_ALLOC_HEAP",code);
        return false;
    }
    std::memset(bgft_heap,0,1024*1024);
    OrbisBgftInitParams p;
    std::memset(&p,0,sizeof(p));
    p.heap=bgft_heap;p.heapSize=1024*1024;
    result=sceBgftServiceIntInit(&p);
    diagnose("REMOTE_BGFT_INIT",result);
    if(result!=0) {
        bgft_init_error=result;
        return !failed("Không khởi tạo được BGFT",result,error,code);
    }
    bgft_ready=true;
    return true;
}

bool ensure_modules(std::string& error,int32_t& code) {
    if(app_load_attempted && app_load_error!=0) {
        code=app_load_error;
        error="AppInstUtil không nạp được trong phiên này; xem cai_dat.log";
        return false;
    }
    // Tach moi loi goi thanh hai dong de tranh sai dau ngoac khi build.
    int32_t result = load_module("libSceSystemService.sprx", ORBIS_SYSMODULE_INTERNAL_SYSTEM_SERVICE);
    if (failed("Nạp dịch vụ hệ thống", result, error, code)) return false;

    result = load_module("libSceAppInstUtil.sprx", ORBIS_SYSMODULE_INTERNAL_APP_INST_UTIL);
    diagnose("LOCAL_APPINST_LOAD_FIRST",result);
    if(result!=0 && try_optional_jbc()) {
        result=load_module("libSceAppInstUtil.sprx", ORBIS_SYSMODULE_INTERNAL_APP_INST_UTIL);
        diagnose("LOCAL_APPINST_LOAD_AFTER_JBC",result);
    }
    app_load_attempted=true;
    app_load_error=result;
    if (failed("Nạp bộ cài", result, error, code)) return false;

    // ID 0x80000026 cho libSceSysUtil, khong phu thuoc ten enum cua SDK.
    result = load_module("libSceSysUtil.sprx", static_cast<OrbisSysModuleInternal>(0x80000026u));
    if (failed("Nạp tiện ích hệ thống", result, error, code)) return false;

    result = load_module("libSceBgft.sprx", ORBIS_SYSMODULE_INTERNAL_BGFT);
    if (failed("Nạp dịch vụ BGFT", result, error, code)) return false;
    return true;
}

bool ensure_installer(std::string& error,int32_t& code) {
    if(!ensure_modules(error,code))return false;
    if(!app_ready) {
        int32_t v=sceAppInstUtilInitialize();
        if(failed("Khởi tạo bộ cài",v,error,code))return false;
        app_ready=true;
    }
    if(!ensure_remote_bgft(error,code)) return false;
    return true;
}
}
bool submit_local_install_tracked(const std::string& path,int32_t& task_id,std::string& error,int32_t& code) {
    task_id=-1;
    std::lock_guard<std::mutex> guard(installer_lock);
    code=0; error.clear();
    const std::string root="/data/pkg/";
    if(path.compare(0,root.size(),root)!=0 || path.size()<=root.size() ||
       path.find("..")!=std::string::npos || path.find('/',root.size())!=std::string::npos ||
       path.size()<4 || path.compare(path.size()-4,4,".pkg")!=0) {
        error="Đường dẫn PKG không hợp lệ";code=-1;return false;
    }
    struct stat st;
    if(stat(path.c_str(),&st)!=0 || !S_ISREG(st.st_mode) || st.st_size==0) {
        error="Không tìm thấy PKG hoàn chỉnh";code=-1;return false;
    }
    if(!ensure_installer(error,code))return false;
    char title[16]={0};int32_t is_app=0;
    int32_t v=sceAppInstUtilGetTitleIdFromPkg(path.c_str(),title,&is_app);
    if(failed("Không đọc được mã ứng dụng",v,error,code))return false;
    if(!title[0]){error="PKG không có mã ứng dụng";code=-1;return false;}

    int32_t user_id=0;
    sceUserServiceInitialize(nullptr);
    sceUserServiceGetInitialUser(&user_id);
    OrbisBgftDownloadParamEx param;
    std::memset(&param,0,sizeof(param));
    param.params.userId=user_id;
    param.params.entitlementType=5;
    param.params.id="";
    param.params.contentUrl=path.c_str();
    param.params.contentExUrl="";
    param.params.contentName=title;
    param.params.iconPath="";
    param.params.skuId="";
    param.params.playgoScenarioId="0";
    param.params.releaseDate="";
    param.params.packageType="";
    param.params.packageSubType="";
    param.params.option=ORBIS_BGFT_TASK_OPT_DISABLE_CDN_QUERY_PARAM;
    param.params.packageSize=0;
    param.slot=0;
    OrbisBgftTaskId id=-1;
    v=sceBgftServiceIntDownloadRegisterTaskByStorageEx(&param,&id);
    if(failed("Không tạo được lệnh cài",v,error,code))return false;
    v=sceBgftServiceDownloadStartTask(id);
    if(v!=0) {
        sceBgftServiceIntDownloadUnregisterTask(id);
        failed("Không bắt đầu được cài",v,error,code);
        return false;
    }
    task_id=static_cast<int32_t>(id);
    diagnose("Đã gửi lệnh cài (chưa xác minh hoàn tất)",0);
    return true;
}

bool submit_local_install(const std::string& path,std::string& error,int32_t& code) {
    int32_t task_id=-1;
    return submit_local_install_tracked(path,task_id,error,code);
}

// Cài từ URL: PS4 BGFT tải/cài trực tiếp từ HTTP(S) (theo cơ chế
// đã công bố bởi LightningMods PS4-Store). KHÔNG tải thêm vào /data/pkg.
// Thành công ở đây chỉ là BGFT nhận tác vụ, không chứng minh đã cài xong.
bool submit_remote_install(const std::string& url, const std::string& name,
                           int32_t& task_id, std::string& error, int32_t& code) {
    std::lock_guard<std::mutex> guard(installer_lock);
    task_id = -1;
    code = 0;
    error.clear();
    if ((url.compare(0, 7, "http://") != 0 && url.compare(0, 8, "https://") != 0) ||
        url.size() > 1700 || url.find_first_of("\r\n\t\"<> ") != std::string::npos ||
        url.find('@') != std::string::npos) {
        error = "Liên kết tải không hợp lệ";
        code = -1;
        return false;
    }
    if (!ensure_remote_bgft(error, code)) return false;

    int32_t user_id = 0;
    sceUserServiceInitialize(nullptr);
    const int32_t user_result = sceUserServiceGetInitialUser(&user_id);
    diagnose("REMOTE_USER_ID",user_result);
    if (failed("Không lấy được tài khoản PS4", user_result, error, code)) return false;

    // PS4 BGFT accepts a URL and performs the transfer + install itself.
    // No local PKG is created here; current X download path remains untouched.
    // Be conservative about contentName buffer and the uint32 packageSize ABI.
    const std::string title = name.empty() ? "ChepGame PKG" : name.substr(0, 200);
    OrbisBgftDownloadParam params;
    std::memset(&params, 0, sizeof(params));
    params.userId = user_id;
    params.entitlementType = 5;
    params.id = "";
    params.contentUrl = url.c_str();
    params.contentExUrl = "";
    params.contentName = title.c_str();
    params.iconPath = "";
    params.skuId = "";
    params.option = ORBIS_BGFT_TASK_OPT_DISABLE_CDN_QUERY_PARAM;
    params.playgoScenarioId = "0";
    params.releaseDate = "";
    params.packageType = "";
    params.packageSubType = "";
    params.packageSize = 0; // Don't truncate PKGs larger than 4 GiB.

    OrbisBgftTaskId id = -1;
    // PS4 Themes host invokes IntDebugDownloadRegisterPkg, whereas v0.4.0
    // called IntDownloadRegisterTask. Both are PS4 SDK exports, but the
    // DEBUG path is UNVERIFIED on this firmware. Try it once in Mode 2 only.
    int32_t result = sceBgftServiceIntDebugDownloadRegisterPkg(&params,&id);
    diagnose("REMOTE_DEBUG_REGISTER",result);
    if (result!=0) {
        // Fallback one time only; never use a task id from failed registration.
        id=-1;
        result=sceBgftServiceIntDownloadRegisterTask(&params,&id);
        diagnose("REMOTE_NORMAL_REGISTER",result);
    }
    diagnose("REMOTE_REGISTER_TASK",result);
    if (failed("BGFT từ chối tác vụ tải và cài", result, error, code)) return false;
    result = sceBgftServiceIntDownloadStartTask(id);
    diagnose("REMOTE_INT_START_TASK",result);
    if (result != 0) {
        // Only unregister an unstarted task. Do not delete user PKGs.
        sceBgftServiceIntDownloadUnregisterTask(id);
        failed("Không khởi động được tác vụ BGFT", result, error, code);
        return false;
    }
    task_id = id;
    diagnose("REMOTE_BGFT_TASK_ID",id);
    diagnose("BGFT đã nhận tác vụ tải và cài (chưa xác minh hoàn tất)", 0);
    return true;
}
// Only reads the PS4 BGFT background task. This is not an installation success
// signal: 100% transferred does not guarantee package installation succeeded.
bool query_remote_progress(int32_t task_id, RemoteProgress& out,
                           std::string& error, int32_t& code) {
    std::lock_guard<std::mutex> guard(installer_lock);
    out=RemoteProgress();code=0;error.clear();
    if(task_id<0 || !bgft_ready) {
        error="Chưa có tác vụ BGFT";code=-1;return false;
    }
    OrbisBgftTaskProgress p;
    std::memset(&p,0,sizeof(p));
    int32_t r=sceBgftServiceDownloadGetProgress(task_id,&p);
    if(r!=0) {
        error="Không đọc được tiến độ BGFT";code=r;
        diagnose("REMOTE_GET_PROGRESS",r);
        return false;
    }
    out.transferred=p.transferredTotal;
    out.total=p.lengthTotal;
    out.rest_seconds=p.restSec;
    out.service_error=p.errorResult;
    out.bits=p.bits;
    if(p.errorResult!=0) {
        error="BGFT báo lỗi tải/cài";code=p.errorResult;
        diagnose("REMOTE_TASK_ERROR",code);
        return false;
    }
    return true;
}
} // namespace chepgame
