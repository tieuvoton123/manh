# CHEPGAME.NET Store v0.4.5 — FIX WORKFLOW, LIÊN KẾT SDK VÀ THƯ MỤC DỰ PHÒNG

**Ứng dụng tải PKG riêng**, không cài trực tiếp. Title ID `CHEP00001`. PC Server v0.5 giữ nguyên. Installer `CHEP00002` không bị thay đổi.

## Vì sao v0.4.3 có thể báo “Không thể kiểm tra thư mục /data/pkg”?

Mã cũ gọi `lstat("/data/pkg/ten.pkg")` rồi chỉ dựa vào `errno != ENOENT` để kết luận không được phép truy cập. Đồng thời nó gọi `mkdir("/data/pkg")` mà không kiểm tra kết quả. Cách đó không đủ phân biệt tình huống chưa có file, chưa có thư mục, lỗi quyền và lỗi ánh xạ libc/PS4.

## v0.4.4 làm gì khác?

1. Kiểm tra thư mục trước khi mở mạng, tự tạo nếu thiếu. **Thực sự thử tạo một file thử 1 byte bằng `O_CREAT|O_EXCL`, rồi đóng và xóa.** Không chỉ đọc `errno` từ một lệnh `lstat` thất bại.
2. Nếu `/data/pkg` có quyền ghi, tải về `/data/pkg/<id>-<version>.pkg.downloading`; sau kiểm tra, mới chuyển sang `.pkg`.
3. Nếu `/data/pkg` không ghi được nhưng `/data/ChepGameStore/downloads` ghi được, tự tải vào **thư mục dự phòng**, và thông báo rõ đường dẫn. **PKG trong thư mục dự phòng KHÔNG tự hiện trong GoldHEN HDD Installer.** Chuyển file sang `/data/pkg` bằng FTP sau khi tải.
4. Nếu cả hai không ghi được, hiện mã lỗi của từng thư mục và ghi `DIR_BOTH_FAILED` vào `/data/ChepGameStore/tai_pkg.log` nếu vùng log cho phép ghi.
5. Trước khi tải, kiểm tra file `.pkg` đã tồn tại ở **cả hai thư mục**; không tự ghi đè file cũ. Kiểm tra header, kích thước nếu catalog có, và SHA-256 nếu catalog cung cấp.
6. Giữ cơ chế HTTP Range, kiểm tra dữ liệu trùng 64 KiB, retry 4 lần, theo dõi speed/ETA, và chặn bấm X lặp đã có từ v0.4.3.
7. Đã bổ sung kiểm tra cú pháp **`src/main.cpp`** bằng OpenOrbis SDK trên GitHub Actions, thay vì chỉ kiểm tra phần HTTP và font.

## Cài bản hotfix

**`UPDATE_REPO.zip`**: giải nén vào repo đã dùng v0.4.3, ghi đè đúng đường dẫn. Chạy **Actions → Build ChepGame Store PS4 PKG → Run workflow**. Artifact dự kiến là `ChepGame-Store-PS4-v0.4.4-PKG`.

**`FULL_SOURCE.zip`**: mã tạo nguồn đầy đủ từ upstream đã ghim. Không chứa `stb_truetype.h` giả dùng cho test. Workflow tải file header thật và xác minh SHA-256 trước khi tạo nguồn.

Sau khi cài v0.4.4, thử PKG homebrew nhỏ. Để xem file:
- Đích bình thường: `/data/pkg/`
- Dự phòng nếu Store không có quyền ghi ở đích bình thường: `/data/ChepGameStore/downloads/`
- Log: `/data/ChepGameStore/tai_pkg.log`

**Không xóa** `.pkg` hoặc `.downloading` từ v0.4.3 trước khi kiểm tra qua FTP. Nếu `.downloading` có metadata `.resume`, Store sẽ cố tải tiếp ở đúng thư mục đó. Nếu thư mục gốc mất quyền ghi, phải xử lý quyền trước; đừng copy tùy tiện file dở qua vị trí khác rồi mong tự nối.

## Giới hạn kiểm thử

Mã đã qua kiểm thử hồi quy bằng C++/Python trên PC, gồm kiểm tra thư mục, từ chối symlink, file PKG cũ, resume, mất mạng và HTTP byte-count. **Chưa biên dịch bằng SDK PS4 trong môi trường này và chưa được xác minh trên PS4 của mày**. Các trường hợp do sandbox/GoldHEN giới hạn quyền ở cả hai thư mục sẽ cần xử lý trên máy; phần mềm không thể tự vượt quyền chỉ bằng thay đổi `errno`.


## Hotfix v0.4.5 (2026-10-09)

- Sửa tên module test trong workflow: `tests.test_download_stable_v044` không tồn tại, tên đúng là `tests.test_download_stable_v043`.
- Giữ liên kết thư viện `-lSceAppInstUtil -lSceBgft` vì hiện tại source còn hàm BGFT và UI tham chiếu dù thao tác X chỉ tải về. Bản cũ xóa thư viện quá sớm khiến build/link có nguy cơ thất bại.
- Khi chọn lưu vào `/data/ChepGameStore/downloads`, tạo trước thư mục cha `/data/ChepGameStore` nếu chưa tồn tại.
- Installer v0.3.3 hỗ trợ quét cả `/data/pkg` và thư mục Store dự phòng; không cần tự chuyển file qua FTP trước khi *thử* cài bằng Installer riêng. Khả năng BGFT chấp nhận đường dẫn dự phòng phải xác minh trên PS4.
- Không thay đổi URL mặc định, cấu hình PC Server, Title ID, HTTP Range, SHA, và không xóa bất kỳ `.pkg` cũ nào.
- Nếu tải vẫn lỗi, hãy xem `/data/ChepGameStore/tai_pkg.log` và đường dẫn catalog trong mục chọn máy chủ của Store. Cần cả màn hình lỗi để biết lý do HTTP chính xác.
- 18 kiểm thử Store trên host với fixture test-only đạt. Chưa chạy được OpenOrbis SDK/PS4 thực tế; kết quả kiểm thử không bảo đảm cài đặt chạy được trên máy.
