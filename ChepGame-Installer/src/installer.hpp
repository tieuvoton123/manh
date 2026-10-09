#pragma once
#include <cstdint>
#include <string>

namespace chepinstaller {
struct InstallerResult {
    bool accepted;
    int32_t code;
    int32_t task_id;
    std::string step;
    std::string title_id;
    InstallerResult():accepted(false),code(0),task_id(-1){}
};
// Submits one local /data/pkg/*.pkg task. Never uninstalls, deletes or overwrites packages.
InstallerResult begin_install(const std::string& absolute_path);
// Poll is best-effort, not a guarantee of complete installation.
bool get_progress(int32_t task_id,unsigned& percent,int32_t& error_code);
bool can_install_with_jbc();
// Attempt module initialization before scanning directories outside app sandbox.
bool enable_hdd_scan_access();
}
