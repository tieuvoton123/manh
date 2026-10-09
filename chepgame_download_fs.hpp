#pragma once
// Native PS4 / host C++11 filesystem checks, without relying on errno after a failed lstat.
// Probe creates one exclusive temporary byte, then removes it; no PKG is touched.
#include <cerrno>
#include <cstdio>
#include <cstdint>
#include <fcntl.h>
#include <string>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

namespace chepgame {

inline bool regular_file(const std::string& file, uint64_t& length) {
    struct stat st;
    if (lstat(file.c_str(), &st) != 0 || !S_ISREG(st.st_mode) || st.st_size < 0)
        return false;
    length = static_cast<uint64_t>(st.st_size);
    return true;
}

inline bool file_entry_exists(const std::string& file) {
    struct stat st;
    return lstat(file.c_str(), &st) == 0;
}

inline bool ensure_writable_dir(const std::string& path, std::string& detail, int& code) {
    code = 0;
    struct stat st;
    // /data/ChepGameStore/downloads may be used before the log/config folder exists.
    // Create only the one fixed, known parent; never create arbitrary parent paths.
    if (path == "/data/ChepGameStore/downloads") {
        struct stat parent;
        if (lstat("/data/ChepGameStore", &parent) != 0) {
            if (mkdir("/data/ChepGameStore", 0777) != 0 &&
                lstat("/data/ChepGameStore", &parent) != 0) {
                code=errno;
                detail="cannot create Store parent (errno="+std::to_string(code)+")";
                return false;
            }
        }
        if (lstat("/data/ChepGameStore", &parent) != 0 || !S_ISDIR(parent.st_mode)) {
            code=ENOTDIR; detail="invalid Store parent"; return false;
        }
    }
    if (lstat(path.c_str(), &st) != 0) {
        // Try mkdir even if libc reported an unreliable errno from lstat.
        if (mkdir(path.c_str(), 0777) != 0 && lstat(path.c_str(), &st) != 0) {
            code = errno;
            detail = "mkdir/inspect " + path + " (errno=" + std::to_string(code) + ")";
            return false;
        }
    }
    if (lstat(path.c_str(), &st) != 0 || !S_ISDIR(st.st_mode)) {
        code = errno;
        detail = "not a writable directory: " + path;
        return false;
    }
    for (unsigned i = 0; i < 16; ++i) {
        const std::string probe = path + "/.chepgame_probe_" +
            std::to_string(static_cast<unsigned long>(getpid())) + "_" + std::to_string(i);
        const int fd = open(probe.c_str(), O_CREAT | O_EXCL | O_WRONLY, 0600);
        if (fd < 0) {
            code = errno;
            if (code == EEXIST) continue;
            detail = "no write access: " + path + " (errno=" + std::to_string(code) + ")";
            return false;
        }
        const char marker = 'C';
        const bool written = write(fd, &marker, 1) == 1;
        const int saved = written ? 0 : errno;
        const int closed = close(fd);
        const int close_code = errno;
        const int unlinked = unlink(probe.c_str());
        if (!written || closed != 0 || unlinked != 0) {
            code = written ? (closed ? close_code : errno) : saved;
            detail = "write/close/cleanup failed: " + path + " (errno=" + std::to_string(code) + ")";
            return false;
        }
        detail.clear();
        code = 0;
        return true;
    }
    detail = "probe filenames occupied: " + path;
    code = EEXIST;
    return false;
}

inline bool pkg_magic_ok(const std::string& path) {
    FILE* f = std::fopen(path.c_str(), "rb");
    if (!f) return false;
    unsigned char magic[4] = {0,0,0,0};
    const bool read = std::fread(magic, 1, 4, f) == 4;
    std::fclose(f);
    return read && magic[0] == 0x7f && magic[1] == 'C' &&
           magic[2] == 'N' && magic[3] == 'T';
}

} // namespace chepgame
