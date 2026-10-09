#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace chepinstaller {
struct PackageFile {
    std::string filename;
    std::string full_path;
    uint64_t size;
    uint64_t inode;
    uint64_t device;
    int64_t modified_time;
};
// Only plain, non-symlink, complete-looking .pkg files directly in /data/pkg.
// No traversal or recursion. Checks PS4 PKG magic; does not guarantee signature/integrity.
bool scan_packages(const std::string& folder, std::vector<PackageFile>& results, std::string& error);
std::string pretty_bytes(uint64_t n);
// Aggregate HDD Store primary and fallback locations, preserving full source paths.
bool scan_package_locations(const std::vector<std::string>& directories,
                            std::vector<PackageFile>& results, std::string& error);
// Snapshot comparison before beginning install; catches files changed since the UI scanned them.
bool unchanged_package(const PackageFile& file);
}
