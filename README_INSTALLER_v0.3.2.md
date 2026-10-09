# CHEPGAME.NET INSTALLER – BY SUPER MANH (PS4 HDD-only v0.3.2)

## Thiết kế mới: HAI ứng dụng hoàn toàn độc lập

- **ChepGame Store:** app hiện tại của bạn, chỉ dùng nút **X – Tải** và lưu PKG đã hoàn chỉnh vào `/data/pkg/`. Không cần sửa Store hoặc PC Server v0.5.
- **ChepGame Installer:** ứng dụng PS4 riêng, Title ID **CHEP00002** (không ghi đè Store CHEP00001). Chỉ quét `/data/pkg/*.pkg`, cho chọn rồi xác nhận cài.

Ứng dụng cài không tải internet, không cập nhật catalog, không đọc dữ liệu riêng của Store, không tự xóa PKG, không gỡ game. Chỉ nhận file `.pkg` có header PS4 PKG `7f 43 4e 54` và dung lượng >= 4096 byte. Đây là kiểm tra sơ bộ; AppInstUtil chịu trách nhiệm đọc Title ID, hệ thống chịu trách nhiệm xác minh gói.

## QUAN TRỌNG: JBC CẦN THIẾT CHO MÁY CỦA BẠN

Log thực tế của máy cho thấy `AppInstUtil` lỗi `0x80020008` nếu không kích hoạt JBC. Một bộ thử module trước đó nạp JBC thành công và sau đó AppInstUtil nạp thành công. Do đó **Installer này KHÔNG được quảng cáo là có thể cài nếu thiếu module JBC tương thích với PS4 9.00 GoldHEN 2.4b18.9**.

**Ưu tiên** sử dụng `libjbc.sprx` đã thử thành công trên máy của bạn (có export `Jailbreak`), rồi đặt tại:

`ChepGame-Installer/assets/libjbc.sprx`

Nếu không có file, workflow **tự tải một bản công khai đã ghim** từ `0x199/ps4-ipi` (commit và Git blob SHA được kiểm tra trong `fetch_jbc.py`). Đây KHÔNG phải file đã được xác minh tương thích với GoldHEN 2.4b18.9 của bạn. Chỉ thử với PKG homebrew nhỏ và chấp nhận rủi ro treo máy. Chọn `diagnostic_without_jbc=true` để build giao diện không cài game khi không có module.

## Cách thêm vào repo GitHub hiện tại (ví dụ repo `manh`)

1. Giải nén **UPDATE_REPO.zip**. Upload thư mục `ChepGame-Installer/` và `.github/workflows/build-chepgame-installer.yml` lên gốc repo, giữ nguyên cấu trúc thư mục.
2. Không bắt buộc upload `libjbc.sprx` nữa: GitHub Actions tự tải bản PS4-IPI được ghim và xác minh SHA nếu thiếu. Muốn ưu tiên module đã chạy được trên PS4, tự đặt nó ở `ChepGame-Installer/assets/libjbc.sprx`.
3. Vào **GitHub Actions -> Build ChepGame PKG Installer (Standalone PS4) -> Run workflow**.
4. Tải artifact `CHEPGAME-NET-Installer-PS4-v0.3.2`, chứa `ChepGame-Installer-PS4-v0.3.2.pkg`.
5. Cài PKG Installer bằng **GoldHEN Package Installer** một lần. Sau đó Installer xuất hiện như ứng dụng riêng ngoài PS4 Home.
6. Dùng **Store** để tải game PKG xong rồi mở **Installer**, chọn game, nhấn X hai lần để xác nhận.

## Điều khiển

- D-pad lên/xuống: chọn PKG.
- **X:** chọn/cài (phải xác nhận lần hai).
- **□:** quét lại `/data/pkg/` sau khi Store tải xong.
- **O:** quay lại/hủy xác nhận; từ danh sách sẽ thoát về PS4 Home.
- Màn hình hiển thị tên file, dung lượng, mã tác vụ và ước lượng tiến độ BGFT nếu đọc được.

## An toàn/giới hạn

- **Không bấm cài liên tục:** 1 tác vụ cho mỗi phiên mở Installer, tránh task trùng hoặc các game/patch chồng nhau.
- BGFT chấp nhận tác vụ **không có nghĩa đã cài xong**. Kiểm tra PS4 Notifications / Downloads và game ngoài màn hình Home.
- Không thực thi AppUnInstall, không tự xóa file PKG; khi thiếu dung lượng, báo `INSUFFICIENT_FREE_SPACE`.
- Với HDD, nên có thêm dung lượng trống bằng dung lượng PKG + khoảng 256 MB tối thiểu; thực tế có thể cần nhiều hơn.
- Ghi log: `/data/ChepGameInstaller/installer.log`. Nếu lỗi, gửi log này để xử lý.
- App chưa qua kiểm thử firmware/hardware thật; kiểm thử C++ dùng OpenOrbis headers sẽ được GitHub Actions thực hiện.

## Kiểm thử cục bộ

`cd ChepGame-Installer && python3 -m unittest discover -s tests -v`

## Tài liệu tham khảo

- PS4 Internal PKG Installer: https://github.com/0x199/ps4-ipi
- PS4 Remote PKG Installer: https://github.com/flatz/ps4_remote_pkg_installer
- GoldHEN: https://github.com/GoldHEN/GoldHEN
- Font bitmap rasterized từ Noto Sans, giấy phép SIL OFL: `ChepGame-Installer/NOTO_LICENSE.txt`. Không kèm font file.

## Các thay đổi trong bản v0.3

- Bộ quét và bộ cài đều tái kiểm tra file PKG thật trước khi thao tác; ngăn symlink giả và đổi inode/size giữa lúc quét và đọc.
- Chặn sự kiện nút X lặp rất nhanh (400 ms) để tránh gửi lệnh ngay khi hộp xác nhận vừa mở.
- Dừng vòng polling khi BGFT báo lỗi, không spam lại trạng thái thất bại.
- Ưu tiên `localCopyPercent` (tiến độ sao chép trên HDD); số byte BGFT chỉ là số liệu tham khảo vì trường SDK là 32-bit.
- Giữ ứng dụng Store v0.4.3 và đường tải `/data/pkg/` hoàn toàn độc lập.

## Phân biệt hai chế độ build

- **Build có bộ cài:** Workflow lấy module JBC tại `assets/libjbc.sprx` nếu có, nếu không sẽ tải từ PS4-IPI đã ghim và kiểm tra Git blob hash. Khả năng chạy `Jailbreak` và cài game vẫn phải xác minh trên PS4.
- **Diagnostic UI:** Với `diagnostic_without_jbc=true`, workflow không tải hoặc đóng gói JBC, ngay cả khi repo có file; app chỉ hiện danh sách và ghi lỗi thiếu module, **không cài được game**.

Bộ nguồn này **chưa phải file `.pkg` đã biên dịch**. Việc đóng gói PKG được thực hiện bằng workflow OpenOrbis trên GitHub, vì môi trường làm việc hiện tại chưa có PS4 SDK và vẫn chưa có xác nhận tương thích của module JBC trên máy PS4 của bạn.


## An toàn trạng thái tác vụ (v0.3)
- Sau khi PS4 nhận BGFT task, ứng dụng ghi `/data/ChepGameInstaller/pending_task.txt`. Khi mở lại, vẫn hiện tác vụ chưa xác minh; không tự đăng ký lại.
- Bấm △ và xác nhận X CHỈ SAU KHI kiểm tra Notifications/Downloads của PS4. Thao tác chỉ xóa ghi nhớ tác vụ, **không** xác minh cài xong, không xóa PKG/game.
- Nếu có lỗi AppInstUtil/JBC/BGFT, xem `/data/ChepGameInstaller/installer.log`. Log cũ tự xoay vòng ở ~256KB.
- Trước khi cài, xác minh file vẫn giữ nguyên kích thước, thời gian sửa và inode so với lúc quét. Điều này không thay thế kiểm tra chữ ký/độ nguyên vẹn PKG.
- Build chẩn đoán thiếu `libjbc.sprx` sẽ KHÔNG CÀI ĐƯỢC game. Build bình thường sẽ tải bản từ PS4-IPI có kiểm tra hash nếu cần.
- Kết quả kiểm thử chỉ trên host C++/stubs; chưa kiểm chứng build SDK thật và PS4 thật.

## Các lưu ý an toàn bản v0.3
- Installer chặn tác vụ trùng qua file ghi nhớ. Nếu file ghi nhớ lỗi, app cũng khóa cài mới cho tới khi người dùng kiểm tra PS4 Downloads và xác nhận thủ công.
- Không đọc được dung lượng trống: từ chối gửi lệnh cài. Không đủ dung lượng: từ chối trước khi khởi tạo bộ cài.
- Tác vụ đã gửi không có nghĩa game đã cài xong. Chỉ thông báo hệ thống PS4 xác nhận kết quả.

## Hotfix v0.3.2 – Giải quyết lỗi Missing libjbc.sprx

- Lỗi build cũ: dừng ngay ở `ERROR: Missing ChepGame-Installer/assets/libjbc.sprx`.
- Mới: `ChepGame-Installer/fetch_jbc.py` tự tải module PS4 SELF từ `https://github.com/0x199/ps4-ipi` tại commit `687fb0ea675994f8bc9f2dc2b0ce1ca82e8092e0` nếu thiếu.
- Xác minh chính xác Git blob SHA-1 `281946bfa3803426da3a48e78f647349400986f9`, kích thước `9952` và magic PS4 SELF trước khi ghi. Không bỏ qua hash và không âm thầm ghi đè module tự cung cấp.
- Không kèm file nhị phân bên thứ ba trong ZIP. Repository nguồn trên GitHub hiện không công bố giấy phép; không tự ý phân phối lại binary ngoài mục đích dùng thử cá nhân khi chưa làm rõ quyền.
- Upstream PS4-IPI từng dùng module này để chạy `Jailbreak`; tuy nhiên kiểm tra file SELF không chứng minh module hoạt động trên firmware/GoldHEN của bạn. Lỗi `JBC_RESOLVE` / `JBC_CALL` hoặc lỗi BGFT vẫn có thể xảy ra trên PS4.
- Không đụng đến Store, không sửa danh sách game, không gỡ hoặc xóa PKG.

**Nếu Actions lại lỗi:** gửi nguyên phần log từ bước `Check installer assets and auto-fetch verified JBC` trở xuống. Nếu chạy được trên PS4 nhưng không cài: gửi `/data/ChepGameInstaller/installer.log`.


## Hotfix v0.3.2 – Chế độ build rõ ràng và bắt buộc module khi cài

- Build mặc định **tự tải** `libjbc.sprx` từ PS4-IPI (commit, Git blob SHA và SELF magic đã ghim) nếu thiếu; nếu tải hoặc kiểm tra lỗi thì Action **dừng** và báo lỗi, không xuất PKG giả cài được.
- `Makefile` bắt buộc JBC khi `DIAGNOSTIC_ONLY=0`, không còn âm thầm loại module khỏi PKG nếu thiếu.
- `diagnostic_without_jbc=true` / `DIAGNOSTIC_ONLY=1` **luôn** loại JBC khỏi PKG (kể cả nếu repo đã có module), đặt hậu tố `-DIAGNOSTIC.pkg`, và **không có khả năng cài game**.
- CI kiểm tra GP4 manifest xem thực sự đóng gói hay không đóng gói `libjbc.sprx`, tạo SHA-256 và tách tên artifact.
- Giữ nguyên Title ID `CHEP00002`, Store `CHEP00001` không bị thay đổi; tên brand được cập nhật.
- Nguồn JBC bên thứ ba được tải lúc build chứ không đi kèm ZIP vì chưa xác nhận được điều khoản phân phối lại.
- **Chưa thể xác nhận bản tải từ PS4-IPI có export `Jailbreak` và chạy được trên thiết bị cụ thể; cần test console và xem `/data/ChepGameInstaller/installer.log`.**

### Cách khắc phục lỗi build cũ

Giải nén ZIP mới vào **gốc repo** sao cho có `.github/workflows/build-chepgame-installer.yml` và `ChepGame-Installer/fetch_jbc.py`. Ghi đè workflow cũ; không dùng lại YAML cũ chứa `ERROR: Missing ChepGame-Installer/assets/libjbc.sprx`. Chạy Actions → `Build ChepGame PKG Installer (Standalone PS4)` → `Run workflow`, để `diagnostic_without_jbc=false`.
