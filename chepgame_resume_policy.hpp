#pragma once
// Free-standing C++11 helpers. No firmware dependencies; can be unit-tested.
#include <stdint.h>
#include <cstdio>
#include <string>
#include <limits>
namespace chepgame {
static const uint64_t kOverlapBytes = 65536;
static const int kMaxRetries = 4;
inline std::string resume_identity(const std::string& url, uint64_t bytes, const std::string& sha) {
    return url + "\n" + std::to_string(bytes) + "\n" + sha + "\n";
}
inline uint64_t overlap_from(uint64_t local) { return local > kOverlapBytes ? local - kOverlapBytes : 0; }
inline bool read_content_range(const std::string& raw, uint64_t& first, uint64_t& last, uint64_t& total) {
    unsigned long long a=0,b=0,c=0; char trailing='\0';
    if (std::sscanf(raw.c_str(), "bytes %llu-%llu/%llu %c", &a,&b,&c,&trailing)!=3) return false;
    first=(uint64_t)a;last=(uint64_t)b;total=(uint64_t)c;
    return total>0 && first<=last && last<total;
}
inline bool range_valid(int code, bool requested, uint64_t requested_start,
                        const std::string& content_range, uint64_t expected_size,
                        uint64_t& server_total) {
    server_total=0;
    if (!requested) return code==200;
    if (code==200) return true; // Server ignored Range: restart from byte zero.
    if (code!=206) return false;
    uint64_t first=0,last=0,total=0;
    if (!read_content_range(content_range,first,last,total) || first!=requested_start) return false;
    if (expected_size && total!=expected_size) return false;
    server_total=total;return true;
}
}
