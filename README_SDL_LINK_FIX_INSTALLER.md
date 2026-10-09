# ChepGame Installer v0.3.3 – PS4 SDL2 linker hotfix

## Lỗi thực tế
`ld.lld-18: error: undefined symbol: sceVideoOutOpen / sceAudioOutInit / scePadOpen` khi biên dịch `eboot.bin`.
Các file `.cpp` đã biên dịch thành công; lỗi thuộc phần liên kết thư viện SDL2 tĩnh với OpenOrbis v0.5.4.

## Đã sửa
- `ChepGame-Installer/Makefile`: thêm `-lSceVideoOut -lSceAudioOut -lScePad` **sau** `-lSDL2`.
- `.github/workflows/build-chepgame-installer.yml`: kiểm tra cả 4 thư viện OpenOrbis trước khi chạy linker, trả lỗi rõ nếu SDK không có thư viện cần thiết.
- `ChepGame-Installer/tests/test_sdl_link_contract.py`: bài kiểm thử hồi quy cho lệnh `ld.lld`, thứ tự tham số và cả hai chế độ build.
- Không chỉnh sửa source Store, JBC, scanner `/data/pkg` hay logic BGFT.

## Cập nhật repo `manh`
Giải nén ZIP UPDATE REPO **tại gốc repo**, ghi đè Makefile và workflow; commit các file. Chạy GitHub Actions → Build ChepGame PKG Installer (Standalone PS4) → Run workflow (`diagnostic_without_jbc=false`).

## Hạn chế kiểm thử
Các kiểm thử dưới đây chỉ xác minh cấu hình linker và code trên PC. Chưa xác nhận bước `ld.lld-18` với **SDK OpenOrbis thực** hay tạo `.pkg` và chạy trên PS4, do môi trường đóng gói không có SDK và PS4. Nếu GitHub Actions báo lỗi mới sau bước link, cần xem log mới để xử lý tiếp.
