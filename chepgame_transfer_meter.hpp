// ChepGame Store transfer estimates.  Independent of platform/SDL for unit testing.
#pragma once
#include <stdint.h>
#include <algorithm>
#include <sstream>
#include <string>

namespace chepgame {

class TransferMeter {
public:
    TransferMeter() { reset(); }
    void reset() {
        initialized_=false;
        speed_valid_=false;
        last_sample_ms_=last_data_ms_=0;
        last_sample_bytes_=last_data_bytes_=0;
        bytes_per_second_=0.0;
    }
    void update(uint64_t bytes, uint32_t now_ms) {
        if (!initialized_ || bytes < last_sample_bytes_) {
            initialized_=true;
            speed_valid_=false;
            last_sample_ms_=last_data_ms_=now_ms;
            last_sample_bytes_=last_data_bytes_=bytes;
            bytes_per_second_=0.0;
            return;
        }
        if (bytes > last_data_bytes_) {
            last_data_bytes_=bytes;
            last_data_ms_=now_ms;
        }
        const uint32_t elapsed=now_ms-last_sample_ms_;  // unsigned subtraction survives SDL tick wrap.
        if (elapsed < 1000) return;
        const uint64_t delta=bytes-last_sample_bytes_;
        const double instantaneous=(double)delta*1000.0/(double)elapsed;
        if (!speed_valid_) {
            bytes_per_second_=instantaneous;
            speed_valid_=true;
        } else {
            // Exponential moving average: dampen a burst without hiding sustained slowdowns.
            bytes_per_second_=0.68*bytes_per_second_+0.32*instantaneous;
        }
        last_sample_ms_=now_ms;
        last_sample_bytes_=bytes;
    }
    bool has_estimate() const { return speed_valid_; }
    bool stalled(uint32_t now_ms) const {
        return initialized_ && now_ms-last_data_ms_>4000;
    }
    double speed(uint32_t now_ms) const {
        return speed_valid_ && !stalled(now_ms) ? bytes_per_second_ : 0.0;
    }
    static uint64_t seconds_remaining(uint64_t completed, uint64_t total, double speed) {
        if (!total || completed>=total || speed<1.0) return 0;
        const double seconds=(double)(total-completed)/speed;
        if (seconds>2592000.0) return 2592000; // 30 days; avoid overflow/unbounded ETA.
        return (uint64_t)(seconds+0.999); // Round upward.
    }
private:
    bool initialized_, speed_valid_;
    uint32_t last_sample_ms_,last_data_ms_;
    uint64_t last_sample_bytes_,last_data_bytes_;
    double bytes_per_second_;
};

inline std::string duration_vi(uint64_t seconds) {
    if (seconds>=86400) {
        std::ostringstream s; s<<seconds/86400<<" ngày "<<(seconds%86400)/3600<<" giờ";return s.str();
    }
    if (seconds>=3600) {
        std::ostringstream s;s<<seconds/3600<<" giờ "<<(seconds%3600)/60<<" phút";return s.str();
    }
    if (seconds>=60) {
        std::ostringstream s;s<<seconds/60<<" phút "<<seconds%60<<" giây";return s.str();
    }
    std::ostringstream s;s<<seconds<<" giây";return s.str();
}

} // namespace chepgame
