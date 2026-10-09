# ChepGame – Hotfix Store v0.4.5 + Installer v0.3.3

Đây là **source update**, KHÔNG phải PKG đã build hoặc đã kiểm thử trên PS4.

## Cài source vào GitHub

1. Dùng repo đang có Store v0.4.4 và Installer v0.3.2; **sao lưu** source hiện tại.
2. Giải nén HOTFIX_UPDATE_REPO.zip vào **gốc** repository; giữ đúng cấu trúc `.github/workflows`, `ChepGame-Installer`, `tests`, `assets` (nếu có), ghi đè các file trùng tên.
3. Giữ nguyên `assets/noto_sans.ttf`, `assets/noto_symbols2.ttf`, `assets/chepgame_icon.png` vốn có trong repo. File cập nhật không phát hành lại font.
4. Chạy GitHub Actions `Build ChepGame Store PS4 PKG`, nhận Store v0.4.5.
5. Chạy `Build ChepGame PKG Installer (Standalone PS4)` với `diagnostic_without_jbc=false`, nhận Installer v0.3.3. Workflow tự tải JBC theo cam kết bản v0.3.2; phải kiểm chứng tương thích trên PS4.
6. Không xóa PKG cũ, `.downloading`, `.resume`, hoặc thay đổi thư mục `/data/pkg`.

## Hai vị trí lưu/đọc PKG

- Chính: `/data/pkg/*.pkg`
- Dự phòng nếu Store không thể ghi thư mục chính: `/data/ChepGameStore/downloads/*.pkg`

Installer v0.3.3 quét hai nơi, đánh dấu `[PKG]` và `[STORE]`. Installer bỏ qua file tải dở `.pkg.downloading`, symlink và header PKG sai. Nó chỉ gọi JBC sau khi bấm □ Làm mới hoặc X xác nhận cài; không tự động thử JBC ngay khi mở.

## Nếu không tải hoặc danh sách trống

- Kiểm tra PC server đang chạy trên LAN; IP trong nút Máy chủ của Store phải khớp máy PC. Mẫu cũ `http://192.168.1.6:8099/orbis/catalog.json` là ví dụ, có thể không còn đúng.
- Kết nối FTP tới PS4 và kiểm tra hai thư mục trên. Nếu thấy `.downloading` nhưng không có `.pkg`, lượt tải chưa hoàn tất hoặc còn lỗi kích thước/SHA.
- Store log: `/data/ChepGameStore/tai_pkg.log`: `DIR_BOTH_FAILED` cho biết thiếu quyền ghi cả hai, `FALLBACK_DIR` là Store dùng thư mục dự phòng, `HTTP_FAIL` liên quan tải HTTP, `READY` hoặc `READY_FALLBACK` là đã công bố PKG.
- Installer log: `/data/ChepGameInstaller/installer.log`: `JBC_NOT_PACKAGED`, `JBC_RESOLVE`, `JBC_CALL`, `APPINST_INIT` và `BGFT_REGISTER_HDD` dùng để xác định lỗi lớp nào.
- Không tự ý xóa file cũ/đổi quyền hệ thống. Có thể dùng GoldHEN Package Installer để kiểm tra một homebrew PKG nhỏ đã hoàn thành trong `/data/pkg`.

## Trạng thái xác minh

- Installer v0.3.3: 36/36 unit/source tests trên Linux PASS.
- Store v0.4.5: 18/18 unit/source tests trên Linux PASS, font rasterizer dùng header stub CHỈ trong test; GitHub workflow sẽ tải header thật có pin hash.
- Không có SDK PS4 hoặc máy PS4 để thực hiện native link/package/runtime test ở đây. Không tuyên bố đã cài PKG thành công trên thiết bị.
