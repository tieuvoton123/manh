"""v0.4.1 BGFT debugging based on OpenOrbis API and the public PS4 Themes host.
No web exploit or third-party PRX is bundled.
"""
from pathlib import Path
import shutil

def apply(source:Path,root:Path):
    mk=source/'Makefile'
    s=mk.read_text(encoding='utf-8')
    assert s.count('VERSION     := 0.40')==1
    s=s.replace('VERSION     := 0.40','VERSION     := 0.41')
    supplied=root/'assets'/'libjbc.sprx'
    if supplied.is_file():
        data=supplied.read_bytes()
        if len(data)<4096 or not data.startswith(b'\x7fELF'):
            raise ValueError('Optional libjbc.sprx not an ELF/PRX; refuse to package')
        dest=source/'sce_module'/'libjbc.sprx'
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(supplied,dest)
        s += '\n# Optional user-provided JBC module; not distributed with this project\n'
        s += 'PACKAGE_FILES += sce_module/libjbc.sprx\n'
        s += 'PACKAGE_ASSETS += sce_module/libjbc.sprx\n'
    mk.write_text(s,encoding='utf-8')
    main=source/'src'/'main.cpp'
    t=main.read_text(encoding='utf-8')
    assert t.count('BY SUPER MANH  v0.40')==1
    t=t.replace('BY SUPER MANH  v0.40','BY SUPER MANH  v0.41')
    main.write_text(t,encoding='utf-8')
    for name in ('chepgame_direct_install.cpp','chepgame_direct_install.hpp'):
        shutil.copyfile(root/name, source/'src'/name)
    with (source/'CHEPGAME_INFO.txt').open('a',encoding='utf-8') as fp:
        fp.write('v0.4.1: optional JBC preflight, one-shot BGFT init, Theme-host debug registration in URL tab. Experimental.\n')
