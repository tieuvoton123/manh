# ChepGame Store v0.4.5 – CI version guard fix

## Lỗi đã sửa
Build Store bị dừng trước khi biên dịch bởi `kiem_tra_giao_dien.py` còn tìm `v0.44` và Makefile `0.44` trong khi `prepare_native.py` sinh mã nguồn v0.45 / VERSION 0.45.

## Phương pháp
- Kiểm tra đúng nhãn UI `BY SUPER MANH  v0.45` bằng biểu thức chính quy.
- Kiểm tra giá trị biến Makefile `VERSION := 0.45`, không chỉ tìm một chuỗi số trong toàn file.
- Giữ nguyên các guard chức năng, không bỏ qua kiểm tra hoặc hạ version.
- Bổ sung `tests/test_ui_build_guard.py` kiểm tra 3 trường hợp: v0.45 PASS, v0.44 UI FAIL, v0.44 Makefile FAIL.
- Workflow Store tự chạy bài test hồi quy này trước khi build.

## Cài đặt bản vá
Giải nén ZIP UPDATE REPO vào gốc repo GitHub (ngang hàng với `prepare_native.py`), ghi đè các file, rồi commit/push. Không phải sửa Store / Installer khác.
GitHub -> Actions -> **Build ChepGame Store PS4 PKG** -> Run workflow.
Nếu thành công, workflow tiếp tục bước OpenOrbis SDK, biên dịch ELF và đóng gói PKG.

## Giới hạn xác minh
Các kiểm thử mô phỏng chạy trên PC, không phải PS4. Môi trường ở đây chưa có OpenOrbis SDK và PS4 nên không thể cam kết build PKG cuối cùng hoặc app chạy trên PS4. Build thành công chỉ khi tất cả các bước Actions và bước kiểm tra artifact đều PASS.
