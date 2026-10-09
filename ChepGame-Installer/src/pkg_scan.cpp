#include "pkg_scan.hpp"
#include <algorithm>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <dirent.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

namespace chepinstaller {
namespace {
bool is_pkg_name(const std::string& name) {
    if(name.size()<5 || name.size()>230 || name[0]=='.' || name.find('/')!=std::string::npos ||
       name.find("..")!=std::string::npos || name.find('\\')!=std::string::npos) return false;
    const size_t n=name.size();
    return name[n-4]=='.' && (name[n-3]=='p'||name[n-3]=='P') &&
           (name[n-2]=='k'||name[n-2]=='K') && (name[n-1]=='g'||name[n-1]=='G');
}
bool read_pkg_info(const std::string& path, struct stat& st) {
    // On some PS4 libc mappings lstat() for entries under /data/pkg is
    // unreliable even when opendir + open work. Trust opened FD + fstat.
    // O_NOFOLLOW keeps untrusted symlinks out of the list.
    int flags=O_RDONLY | O_NONBLOCK;
#ifdef O_NOFOLLOW
    flags |= O_NOFOLLOW;
#else
    struct stat link_stat;
    if (lstat(path.c_str(),&link_stat)!=0 || S_ISLNK(link_stat.st_mode)) return false;
#endif
    const int fd=open(path.c_str(),flags);
    if(fd<0)return false;
    if(fstat(fd,&st)!=0 || !S_ISREG(st.st_mode) || st.st_size<4096){close(fd);return false;}
    unsigned char magic[4]={};
    const ssize_t n=read(fd,magic,sizeof(magic));
    close(fd);
    return n==4 && magic[0]==0x7f && magic[1]=='C' && magic[2]=='N' && magic[3]=='T';
}
bool by_name(const PackageFile& a,const PackageFile& b) {return a.filename<b.filename;}
}
bool unchanged_package(const PackageFile& pkg) {
    struct stat st;
    if(!read_pkg_info(pkg.full_path,st))return false;
    return (uint64_t)st.st_size==pkg.size && (uint64_t)st.st_ino==pkg.inode &&
           (uint64_t)st.st_dev==pkg.device && (int64_t)st.st_mtime==pkg.modified_time;
}
std::string pretty_bytes(uint64_t n) {
    const char* unit[] = {"B","KB","MB","GB","TB"};
    double val=static_cast<double>(n); unsigned k=0;
    while(val>=1024.0 && k<4){val/=1024.0;++k;}
    char b[64]; std::snprintf(b,sizeof(b),k==0?"%.0f %s":"%.2f %s",val,unit[k]);
    return b;
}
bool scan_packages(const std::string& folder,std::vector<PackageFile>& out,std::string& error) {
    out.clear();error.clear();
    DIR* dir=opendir(folder.c_str());
    if(!dir){error="Không mở được "+folder+" (errno="+std::to_string(errno)+")";return false;}
    struct dirent* ent;
    // Stop after a bounded directory enumeration; do not allocate unbounded amounts of memory.
    unsigned visited=0;
    while((ent=readdir(dir))!=nullptr && visited++<4096) {
        const std::string name=ent->d_name;
        if(!is_pkg_name(name))continue;
        const std::string path=folder+"/"+name;
        struct stat st;
        if(!read_pkg_info(path,st))continue;
        PackageFile pkg;pkg.filename=name;pkg.full_path=path;pkg.size=(uint64_t)st.st_size;
        pkg.inode=(uint64_t)st.st_ino;pkg.device=(uint64_t)st.st_dev;
        pkg.modified_time=(int64_t)st.st_mtime;
        out.push_back(pkg);
        if(out.size()>=500)break;
    }
    closedir(dir);
    std::sort(out.begin(),out.end(),by_name);
    if(visited>4096 && out.empty())error="Quá nhiều file trong thư mục /data/pkg";
    return true;
}
}

namespace chepinstaller {
bool scan_package_locations(const std::vector<std::string>& dirs,
                            std::vector<PackageFile>& out, std::string& error) {
    out.clear(); error.clear();
    bool any_accessible=false;
    for(size_t i=0;i<dirs.size();++i){
        std::vector<PackageFile> found;
        std::string problem;
        const bool ok=scan_packages(dirs[i],found,problem);
        any_accessible=any_accessible||ok;
        // The Store fallback is optional: its absence is not a scan failure
        // when /data/pkg is accessible. Other errors remain visible.
        if(!ok && i>0 && problem.find("(errno="+std::to_string(ENOENT)+")")!=std::string::npos)
            continue;
        if(!problem.empty()){
            if(!error.empty())error+=" | ";
            error+=problem;
        }
        // Keep paths intact; two directories may contain files with the same name.
        for(size_t k=0;k<found.size() && out.size()<500;++k)out.push_back(found[k]);
    }
    std::sort(out.begin(),out.end(),[](const PackageFile& a,const PackageFile& b){
        if(a.filename==b.filename)return a.full_path<b.full_path;
        return a.filename<b.filename;
    });
    return any_accessible;
}
}
