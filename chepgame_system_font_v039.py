"""Final replacement of fixed/raster atlas with runtime PS4 system TTF + Noto fallback."""
from pathlib import Path
import shutil

def apply(source:Path,root:Path):
    assert (root/'stb_truetype.h').is_file(),"Run python3 fetch_stb_header.py before prepare_native.py"
    for name in ('stb_truetype.h',):
        shutil.copyfile(root/name,source/'src'/name)
    shutil.copyfile(root/'chepgame_system_font.cpp',source/'src/pixel_font.cpp')
    assert 'stbtt_MakeCodepointBitmap' in (source/'src/pixel_font.cpp').read_text()
    target=source/'assets/noto_sans.ttf';target.parent.mkdir(exist_ok=True,parents=True)
    shutil.copyfile(root/'assets/noto_sans.ttf',target)
    shutil.copyfile(root/'assets/noto_symbols2.ttf',source/'assets/noto_symbols2.ttf')
    shutil.copyfile(root/'NOTO_LICENSE.txt',source/'NOTO_LICENSE.txt')
    shutil.copyfile(root/'NOTO_LICENSE.txt',source/'assets/noto_license.txt')
    makefile=source/'Makefile'
    mk=makefile.read_text(encoding='utf-8')
    assert 'VERSION     := 0.38' in mk
    assert 'PACKAGE_ASSETS := catalog.json' in mk
    mk=mk.replace('VERSION     := 0.38','VERSION     := 0.39')
    mk=mk.replace('PACKAGE_ASSETS := catalog.json','PACKAGE_ASSETS := catalog.json assets/noto_sans.ttf assets/noto_symbols2.ttf assets/noto_license.txt')
    makefile.write_text(mk,encoding='utf-8')
    main=source/'src/main.cpp'
    s=main.read_text(encoding='utf-8')
    assert 'BY SUPER MANH  v0.38' in s
    s=s.replace('BY SUPER MANH  v0.38','BY SUPER MANH  v0.39')
    main.write_text(s,encoding='utf-8')
    info=source/'CHEPGAME_INFO.txt'
    info.write_text(info.read_text(encoding='utf-8')+
      'v0.3.9: runtime Sony PS4 TTF if accessible, SIL OFL Noto Sans fallback; true TTF glyph metrics.\n',encoding='utf-8')
