#include "task_guard.hpp"
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <unistd.h>
namespace chepinstaller {
namespace {
bool safe_atom(const std::string& str,size_t max_len) {
    if(str.empty() || str.size()>max_len)return false;
    for(size_t i=0;i<str.size();++i){
        const char c=str[i];
        if((unsigned char)c<32 || c=='/' || c=='\\')return false;
    }
    return true;
}
bool valid(const PendingTask& task) {
    return task.task_id>=0 && safe_atom(task.title_id,17) && safe_atom(task.filename,230) &&
           task.filename.find("..") == std::string::npos;
}
}
bool read_pending_task(const std::string& path, PendingTask& task) {
    task=PendingTask();
    FILE* f=std::fopen(path.c_str(),"rb");if(!f)return false;
    char magic[32]={},id[32]={},title[80]={},name[256]={};
    const bool ok=std::fgets(magic,sizeof(magic),f) && std::fgets(id,sizeof(id),f) &&
                  std::fgets(title,sizeof(title),f) && std::fgets(name,sizeof(name),f);
    std::fclose(f);
    if(!ok || std::strcmp(magic,"CHEP_TASK_V1\n")!=0)return false;
    char* end=nullptr;errno=0;
    const long n=std::strtol(id,&end,10);
    if(errno || !end || (*end!='\n' && *end!='\0') || n<0 || n>2147483647L)return false;
    task.task_id=(int32_t)n;
    task.title_id=title;task.filename=name;
    if(!task.title_id.empty() && task.title_id.back()=='\n')task.title_id.pop_back();
    if(!task.filename.empty() && task.filename.back()=='\n')task.filename.pop_back();
    if(!valid(task)){task=PendingTask();return false;}
    return true;
}
bool write_pending_task(const std::string& path,const PendingTask& task) {
    if(!valid(task))return false;
    const std::string temp=path+".tmp";
    int flags=O_CREAT|O_TRUNC|O_WRONLY;
#ifdef O_NOFOLLOW
    flags|=O_NOFOLLOW;
#endif
    const int fd=open(temp.c_str(),flags,0600);if(fd<0)return false;
    const std::string payload="CHEP_TASK_V1\n"+std::to_string(task.task_id)+"\n"+
                              task.title_id+"\n"+task.filename+"\n";
    const ssize_t written=write(fd,payload.data(),payload.size());
    const bool ok=written==(ssize_t)payload.size() && fsync(fd)==0;
    close(fd);
    if(!ok || rename(temp.c_str(),path.c_str())!=0){std::remove(temp.c_str());return false;}
    return true;
}
bool acknowledge_pending_task(const std::string& path) {
    // Called only on an explicit on-screen confirmation after the user checked PS4 Downloads.
    return unlink(path.c_str())==0 || errno==ENOENT;
}
}
