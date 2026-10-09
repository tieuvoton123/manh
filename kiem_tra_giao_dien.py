#!/usr/bin/env python3
"""Build guard: fail CI if a stale/untranslated UI is accidentally packaged."""
import pathlib
import re
import sys

root=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else 'ChepGameStore-PS4')
src=root/'src'
main=(src/'main.cpp').read_text(encoding='utf-8')
url=(src/'chepgame_url_ui.cpp').read_text(encoding='utf-8')
installer=(src/'chepgame_direct_install.cpp').read_text(encoding='utf-8')
mk=(root/'Makefile').read_text(encoding='utf-8')
font=(src/'pixel_font.cpp').read_text(encoding='utf-8')
assert 'stbtt_MakeCodepointBitmap' in font and 'stbtt_GetCodepointHMetrics' in font
assert 'glyph_font' in font and '/preinst/common/font/DFHEI5-SONY.ttf' in font
assert (root/'assets/noto_sans.ttf').is_file() and (root/'assets/noto_symbols2.ttf').is_file() and (root/'assets/noto_license.txt').is_file()
errors=[]
for term in ['BRAND OK','TRIANGLE REFRESH','X DOWNLOAD','NO ENABLED PACKAGES','X   VỀ PS4 ĐỂ CÀI']:
    if term in main+url:errors.append('Còn chuỗi cũ: '+term)
for term in ['v0.44','Tốc độ:', 'Còn lại:', 'Đã tải:', 'fit_text',  'JobBatoInstall','chepgame_active_tab','tab_status[3]','JobRemoteInstall','submit_remote_install','Thư viện','Làm mới','CHEPGAME.NET']:
    if term not in main+url:errors.append('Thiếu: '+term)
for term in ['0.44','-lSceBgft','-lSceAppInstUtil']:
    if term not in mk:errors.append('Makefile thiếu: '+term)
# FontTools unicode coverage is independently tested against both bundled open fonts.
if 'assets/noto_sans.ttf' not in mk or 'assets/noto_symbols2.ttf' not in mk:
    errors.append('Chưa đóng gói font Unicode dự phòng')
if 'chepgame_amsi_font.cpp' in font or 'kRle[]' in font:
    errors.append('Mã nguồn vẫn dùng atlas Amsi cũ')
for term in ['query_remote_progress(', 'sceBgftServiceDownloadGetProgress', 'REMOTE_LOAD_BGFT', 'REMOTE_REGISTER_TASK']:
    if term not in installer:errors.append('Thiếu BGFT probe: '+term)
for term in ['bgft_probe_error', 'BGFT #']:
    if term not in main:errors.append('Thiếu BGFT status UI: '+term)
if 'int main(int, char**)' in main and 'bgft_poll_id' not in main:
    errors.append('Thiếu BGFT polling trong vòng lặp PS4')
if errors:
    print('\n'.join(errors),file=sys.stderr)
    sys.exit(1)
print('Giao diện tiếng Việt OK: bố cục cột tách riêng, tốc độ tải, ETA, Sony TTF + Noto Sans, không còn BRAND OK.')

# The download-only Store must not advertise BGFT and must verify PKGs.
if 'if (false && remote_install' not in main or 'magic[0]==0x7f' not in main:
    raise SystemExit('Download-only safety guard missing')

# Guard against the 100%-then-redownload regression.
client=(src/'http_client.cpp').read_text(encoding='utf-8')
for value in ('download_finished', 'chepgame_download_click', 'chepgame_x_down', 'tai_pkg.log'):
    if value not in main: raise SystemExit('Thieu chong download loop: '+value)
for value in ('sceHttpGetResponseContentLength(handles.req', 'completed==expected_size', 'network_read_error'):
    if value not in client: raise SystemExit('Thieu xac minh hoan tat HTTP: '+value)

# v0.4.4 regression guard: verify directory write preflight and truthful fallback label.
for value in ('ensure_writable_dir(', 'FALLBACK_DIR', 'DIR_BOTH_FAILED', 'existing_sha!=item.sha256', 'chepgame_target_dir'):
    if value not in main: raise SystemExit('v0.4.4 missing: '+value)
assert (src/'chepgame_download_fs.hpp').is_file()
assert 'if(errno!=ENOENT)' not in main
