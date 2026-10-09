#pragma once
#include <stdint.h>
#include <string>
namespace chepgame {
// Only requests BGFT to install a verified PKG that already exists on the HDD.
// A positive return means that BGFT accepted the task, NOT that installation finished.
// The tracked API returns a task id for the HDD and Bato-style tabs.
bool submit_local_install_tracked(const std::string& path, int32_t& task_id,
                                  std::string& error, int32_t& code);
// Compatibility wrapper for the existing install prompt.
bool submit_local_install(const std::string& path, std::string& error, int32_t& code);
// Trả về true nếu BGFT chấp nhận tác vụ từ URL; chưa xác minh cài đặt xong.
bool submit_remote_install(const std::string& url, const std::string& name,
                           int32_t& task_id, std::string& error, int32_t& code);
}

namespace chepgame {
struct RemoteProgress {
    uint32_t transferred, total, rest_seconds, bits;
    int32_t service_error;
    RemoteProgress():transferred(0),total(0),rest_seconds(0),bits(0),service_error(0){}
};
// Poll an existing task, without cancelling it or marking the PKG installed.
bool query_remote_progress(int32_t task_id, RemoteProgress& out,
                           std::string& error, int32_t& code);
}
