"""Bridge pass after v0.3.5: metrics-aware URL cursor, version label and present flush."""
from pathlib import Path

def apply(source: Path, root: Path):
    mk=source/'Makefile'
    text=mk.read_text(encoding='utf-8')
    assert text.count('VERSION     := 0.35')==1
    mk.write_text(text.replace('VERSION     := 0.35','VERSION     := 0.37'),encoding='utf-8')
    main=source/'src/main.cpp'
    code=main.read_text(encoding='utf-8')
    assert 'BY SUPER MANH   v0.35' in code
    code=code.replace('BY SUPER MANH   v0.35','BY SUPER MANH   v0.37')
    # SDL software textures require flushing rendered commands to the window surface.
    code=code.replace('        SDL_UpdateWindowSurface(window);',
                      '        SDL_RenderPresent(renderer);\n        SDL_UpdateWindowSurface(window);')
    main.write_text(code, encoding='utf-8')
    url=source/'src/chepgame_url_ui.cpp' 
    s=url.read_text(encoding='utf-8')
    old='const int cx=107+(int)(cursor_-first)*18;'
    assert s.count(old)==1
    # This was fixed-width in v0.3.5; our font is proportional.
    s=s.replace(old,'const int cx=107+orbisshelf::text_width(3, text_.substr(first, cursor_-first));')
    url.write_text(s,encoding='utf-8')
    info=source/'CHEPGAME_INFO.txt'
    info.write_text(info.read_text(encoding='utf-8') +
        'v0.3.7: chibi icon + glyph-aware cursor and display flush.\n',encoding='utf-8')
