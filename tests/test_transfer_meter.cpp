#include "../chepgame_transfer_meter.hpp"
#include <cassert>
#include <cmath>
#include <iostream>
int main() {
    chepgame::TransferMeter m;
    assert(!m.has_estimate());
    m.update(0, 100);
    m.update(8ull*1024*1024, 1100);
    assert(m.has_estimate());
    assert(std::fabs(m.speed(1200)-8*1024*1024)<2);
    m.update(12ull*1024*1024, 2100);
    assert(m.speed(2200)>4*1024*1024 && m.speed(2200)<8*1024*1024);
    assert(m.stalled(6201));
    assert(m.speed(6201)==0);
    const uint64_t left=chepgame::TransferMeter::seconds_remaining(20,100,10.0);
    assert(left==8);
    assert(chepgame::TransferMeter::seconds_remaining(20,0,10.0)==0);
    assert(chepgame::TransferMeter::seconds_remaining(100,100,10.0)==0);
    assert(chepgame::TransferMeter::seconds_remaining(20,100,0.0)==0);
    m.reset();assert(!m.has_estimate());
    m.update(0,0xfffffc00u);
    m.update(4096,0x00000040u); // 1088 ms, wraparound-safe.
    assert(m.has_estimate());
    assert(chepgame::duration_vi(42)=="42 giây");
    assert(chepgame::duration_vi(492)=="8 phút 12 giây");
    assert(chepgame::duration_vi(4344)=="1 giờ 12 phút");
    assert(chepgame::duration_vi(90000)=="1 ngày 1 giờ");
    std::cout<<"TransferMeter: 17 checks OK\n";
    return 0;
}
