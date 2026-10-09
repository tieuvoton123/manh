#pragma once
#include <cstdint>
#include <string>
namespace chepinstaller {
struct PendingTask {
    int32_t task_id;
    std::string title_id;
    std::string filename;
    PendingTask(): task_id(-1) {}
};
// This journal contains ONLY task metadata, not PKG data. Never deletes a game or its PKG.
bool read_pending_task(const std::string& path, PendingTask& task);
bool write_pending_task(const std::string& path, const PendingTask& task);
bool acknowledge_pending_task(const std::string& path);
}
