#include "installer.hpp"
#include <orbis/AppInstUtil.h>
#include <orbis/Bgft.h>
#include <orbis/Sysmodule.h>
#include <orbis/UserService.h>
#include <orbis/libkernel.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <cctype>
#include <ctime>
#include <fcntl.h>
#include <unistd.h>

namespace chepinstaller {
namespace {
const char* const kLog="/data/ChepGameInstaller/installer.log";
const size_t kHeapSize=1024*1024;
bool jbc_tried=false,jbc_ready=false,modules_ready=false,bgft_ready=false,init_attempted=false;
uint8_t* heap=nullptr;
int32_t init_error=0;
std::string init_step;
void log_step(const char* s,int32_t code) {
    // Prevent unbounded log growth on a console that is used for months.
    struct stat st;
    if(stat(kLog,&st)==0 && st.st_size>256*1024) {
        const std::string rotated=std::string(kLog)+".old";
        std::remove(rotated.c_str());
        std::rename(kLog,rotated.c_str());
    }
    FILE* f=std::fopen(kLog,"a");
    if(f){
        std::fprintf(f,"%lld | %s : 0x%08X\n",(long long)std::time(nullptr),s,(uint32_t)code);
        std::fclose(f);
    }
}
void set_error(InstallerResult& r,const char* step,int32_t code) {
    r.step=step;r.code=code;log_step(step,code);
}
int32_t load_sysmodule(OrbisSysModuleInternal id) {
    const int32_t rc=(int32_t)sceSysmoduleLoadModuleInternal(id);
    return rc>=0?0:rc;
}
bool try_jbc() {
    if(jbc_tried)return jbc_ready;
    jbc_tried=true;
    const char* path="/app0/sce_module/libjbc.sprx";
    struct stat st;
    if(stat(path,&st)!=0 || !S_ISREG(st.st_mode)){
        log_step("JBC_NOT_PACKAGED",-1);return false;
    }
    const int32_t handle=(int32_t)sceKernelLoadStartModule(path,0,nullptr,0,nullptr,nullptr);
    log_step("JBC_LOAD",handle);
    if(handle<=0)return false;
    typedef bool (*JailbreakFn)();
    JailbreakFn jailbreak=nullptr;
    const int32_t rc=sceKernelDlsym(handle,"Jailbreak",reinterpret_cast<void**>(&jailbreak));
    log_step("JBC_RESOLVE",rc);
    if(rc!=0 || !jailbreak)return false;
    // User-provided compatible module; run on explicit X+confirmation only.
    jbc_ready=jailbreak();
    log_step("JBC_CALL",jbc_ready?0:-1);
    return jbc_ready;
}
bool prepare(InstallerResult& r) {
    if(bgft_ready)return true;
    if(init_attempted) {set_error(r,init_step.c_str(),init_error);return false;}
    init_attempted=true;
    // The app never attempts privileged installation if the optional module
    // is missing or has the wrong export; this is a diagnostic-only build.
    if(!try_jbc()) {
        init_error=-1;init_step="JBC_MISSING_OR_FAILED";
        set_error(r,init_step.c_str(),init_error);return false;
    }
    int32_t rc=load_sysmodule(ORBIS_SYSMODULE_INTERNAL_APP_INST_UTIL);
    log_step("LOAD_APPINSTUTIL",rc);
    if(rc<0) {init_error=rc;init_step="LOAD_APPINSTUTIL";set_error(r,init_step.c_str(),rc);return false;}
    rc=load_sysmodule(ORBIS_SYSMODULE_INTERNAL_BGFT);
    log_step("LOAD_BGFT",rc);
    if(rc<0) {init_error=rc;init_step="LOAD_BGFT";set_error(r,init_step.c_str(),rc);return false;}
    rc=load_sysmodule(ORBIS_SYSMODULE_INTERNAL_USER_SERVICE);
    log_step("LOAD_USER_SERVICE",rc);
    if(rc<0) {init_error=rc;init_step="LOAD_USER_SERVICE";set_error(r,init_step.c_str(),rc);return false;}
    rc=sceAppInstUtilInitialize();
    log_step("APPINST_INIT",rc);
    if(rc!=0){init_error=rc;init_step="APPINST_INIT";set_error(r,init_step.c_str(),rc);return false;}
    if(!heap)heap=(uint8_t*)std::malloc(kHeapSize);
    if(!heap){init_error=-1;init_step="BGFT_NO_MEMORY";set_error(r,init_step.c_str(),-1);return false;}
    std::memset(heap,0,kHeapSize);
    OrbisBgftInitParams params;std::memset(&params,0,sizeof(params));
    params.heap=heap;params.heapSize=kHeapSize;
    rc=sceBgftServiceIntInit(&params);
    log_step("BGFT_INIT",rc);
    if(rc!=0){std::free(heap);heap=nullptr;init_error=rc;init_step="BGFT_INIT";set_error(r,init_step.c_str(),rc);return false;}
    modules_ready=true;bgft_ready=true;
    return true;
}
bool safe_file(const std::string& path) {
    const std::string primary="/data/pkg/";
    const std::string fallback="/data/ChepGameStore/downloads/";
    const std::string* prefix=nullptr;
    if(path.compare(0,primary.size(),primary)==0)prefix=&primary;
    else if(path.compare(0,fallback.size(),fallback)==0)prefix=&fallback;
    if(!prefix || path.size()<prefix->size()+5 ||
       path.find('/',prefix->size())!=std::string::npos ||
       path.find("..",prefix->size())!=std::string::npos)return false;
    std::string ext=path.substr(path.size()-4);
    for(size_t i=0;i<ext.size();++i)ext[i]=(char)std::tolower((unsigned char)ext[i]);
    if(ext!=".pkg")return false;
    // Verify by opened descriptor rather than the libc lstat path, which may
    // incorrectly fail on some PS4 filesystems. O_NOFOLLOW
    // and fstat prevent installation through a swapped symlink.
    int flags=O_RDONLY | O_NONBLOCK;
#ifdef O_NOFOLLOW
    flags|=O_NOFOLLOW;
#else
    struct stat st;
    if(lstat(path.c_str(),&st)!=0 || S_ISLNK(st.st_mode))return false;
#endif
    const int fd=open(path.c_str(),flags);if(fd<0)return false;
    struct stat checked;
    if(fstat(fd,&checked)!=0 || !S_ISREG(checked.st_mode) || checked.st_size<4096){
        close(fd);return false;
    }
    unsigned char a[4]={};const ssize_t n=read(fd,a,sizeof(a));close(fd);
    return n==4&&a[0]==0x7f&&a[1]=='C'&&a[2]=='N'&&a[3]=='T';
}
}
bool enable_hdd_scan_access() {
    return try_jbc();
}
bool can_install_with_jbc() {
    struct stat st;return stat("/app0/sce_module/libjbc.sprx",&st)==0&&S_ISREG(st.st_mode);
}
InstallerResult begin_install(const std::string& absolute_path) {
    InstallerResult r;
    if(!safe_file(absolute_path)){set_error(r,"INVALID_PKG_OR_PATH",-1);return r;}
    log_step("PKG_PATH_VALID",0);
    // Local PKG installation commonly needs additional free HDD space.
    // Use a conservative one-file-size margin; never remove the user's PKG.
    struct stat file_stat; struct statvfs disk_stat;
    if(stat(absolute_path.c_str(),&file_stat)!=0 || statvfs("/data",&disk_stat)!=0){
        set_error(r,"FREE_SPACE_CHECK_FAILED",-1);return r;
    }
    const uint64_t free_bytes=(uint64_t)disk_stat.f_bavail*(uint64_t)disk_stat.f_frsize;
    const uint64_t needed=(uint64_t)file_stat.st_size+256ULL*1024ULL*1024ULL;
    if(free_bytes<needed){set_error(r,"INSUFFICIENT_FREE_SPACE",-1);return r;}
    if(!prepare(r))return r;
    char title_id[18]={};int is_app=-1;
    int32_t rc=sceAppInstUtilGetTitleIdFromPkg(absolute_path.c_str(),title_id,&is_app);
    title_id[sizeof(title_id)-1]=0;
    log_step("READ_PKG_TITLE",rc);
    if(rc!=0 || !title_id[0]) {set_error(r,"READ_PKG_TITLE",rc!=0?rc:-1);return r;}
    r.title_id=title_id;
    log_step("PKG_TITLE_RESOLVED",0);
    rc=sceUserServiceInitialize(nullptr);
    // Some PS4 sessions already have the service initialized.
    log_step("USER_SERVICE_INIT",rc);
    int32_t user_id=-1;
    rc=sceUserServiceGetInitialUser(&user_id);
    log_step("USER_ID",rc);
    if(rc!=0 || user_id<0){set_error(r,"USER_ID",rc?rc:-1);return r;}
    OrbisBgftDownloadParamEx params;std::memset(&params,0,sizeof(params));
    params.params.userId=user_id;
    params.params.entitlementType=5;
    params.params.id="";
    params.params.contentUrl=absolute_path.c_str();
    params.params.contentName=title_id;
    params.params.iconPath="";
    params.params.playgoScenarioId="0";
    params.params.option=ORBIS_BGFT_TASK_OPT_DISABLE_CDN_QUERY_PARAM;
    params.slot=0;
    OrbisBgftTaskId task=-1;
    rc=sceBgftServiceIntDownloadRegisterTaskByStorageEx(&params,&task);
    log_step("BGFT_REGISTER_HDD",rc);
    if(rc!=0 || task<0){set_error(r,"BGFT_REGISTER_HDD",rc?rc:-1);return r;}
    // Do not claim installation succeeded merely because a task ID exists.
    rc=sceBgftServiceDownloadStartTask(task);
    log_step("BGFT_START",rc);
    if(rc!=0){set_error(r,"BGFT_START",rc);return r;}
    r.accepted=true;r.task_id=(int32_t)task;r.step="TASK_ACCEPTED_NOT_INSTALLED";
    log_step("TASK_ACCEPTED_NOT_INSTALLED",r.task_id);
    return r;
}
bool get_progress(int32_t id,unsigned& percent,int32_t& err) {
    percent=0;err=0;if(id<0 || !bgft_ready)return false;
    OrbisBgftTaskProgress p;std::memset(&p,0,sizeof(p));
    const int32_t rc=sceBgftServiceDownloadGetProgress(id,&p);
    if(rc!=0){err=rc;return false;}
    if(p.errorResult!=0){err=p.errorResult;return false;}
    // localCopyPercent is preferable for on-HDD installs; transferredTotal
    // is a 32-bit SDK field and may wrap with PKGs larger than 4 GiB.
    if(p.localCopyPercent>0 && p.localCopyPercent<=100)percent=(unsigned)p.localCopyPercent;
    else if(p.lengthTotal>0 && p.transferredTotal<=p.lengthTotal)
        percent=(unsigned)((100ULL*p.transferredTotal)/p.lengthTotal);
    else if(p.numTotal>0)percent=(unsigned)((100ULL*p.numIndex)/p.numTotal);
    if(percent>100)percent=100;
    return true;
}
}
