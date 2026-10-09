#include "chepgame_download_fs.hpp"
#include <cassert>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <string>
#include <sys/stat.h>
#include <unistd.h>

int main() {
    char tmp[] = "/tmp/chepgame-v044-XXXXXX";
    char* base = mkdtemp(tmp);
    assert(base);
    std::string dir = std::string(base) + "/pkg";
    std::string error;
    int code = 0;
    // Recreate absent directory even if caller errno state is polluted.
    errno = EACCES;
    assert(chepgame::ensure_writable_dir(dir, error, code));
    assert(error.empty() && code == 0);
    assert(chepgame::ensure_writable_dir(dir, error, code));
    std::string pkg = dir + "/title.pkg";
    assert(!chepgame::file_entry_exists(pkg));
    FILE* f = fopen(pkg.c_str(), "wb");
    assert(f);
    unsigned char head[] = {0x7f,'C','N','T',0};
    assert(fwrite(head,1,sizeof(head),f) == sizeof(head));
    assert(fclose(f) == 0);
    uint64_t len = 0;
    assert(chepgame::regular_file(pkg, len) && len == sizeof(head));
    assert(chepgame::pkg_magic_ok(pkg));
    std::string symlink_path = dir + "/evil.pkg";
    assert(symlink(pkg.c_str(),symlink_path.c_str()) == 0);
    assert(chepgame::file_entry_exists(symlink_path));
    assert(!chepgame::regular_file(symlink_path,len));
    assert(!chepgame::ensure_writable_dir(pkg,error,code));
    assert(!chepgame::ensure_writable_dir(symlink_path,error,code));
    // A path with a missing parent cannot be created by the downloader.
    assert(!chepgame::ensure_writable_dir(dir+"/missing/sub",error,code));
    assert(unlink(symlink_path.c_str()) == 0);
    assert(unlink(pkg.c_str()) == 0);
    assert(rmdir(dir.c_str()) == 0);
    assert(rmdir(base) == 0);
    puts("v0.4.4 native writable-directory probe / existing PKG: PASS");
}
