#!/usr/bin/env python3
"""Fail closed on trivially broken PS4 PKG artifacts and their build manifests.

This is a structural *post-build* check, NOT a signature verification, SDK build
replacement, jailbreak-compatibility test, or runtime certification.
"""
import argparse
import hashlib
from pathlib import Path
import struct
import sys

MAGIC = b'\x7fCNT'


def verify(pkg_file, gp4_file, sfo_file, title_id, content_id, jbc_mode='ignore'):
    pkg, gp4, sfo = map(Path, (pkg_file, gp4_file, sfo_file))
    if len(title_id) != 9 or len(content_id) != 36 or title_id != content_id[7:16]:
        raise ValueError('Title ID / Content ID mismatch')
    for f in (pkg, gp4, sfo):
        if not f.is_file() or f.stat().st_size == 0:
            raise ValueError('Required build output is missing or empty: ' + str(f))
    if pkg.stat().st_size < 65536:
        raise ValueError('PKG unexpectedly small (<64 KiB): ' + str(pkg))
    with pkg.open('rb') as inp:
        hdr = inp.read(0x1000)
    if hdr[:4] != MAGIC:
        raise ValueError('PKG header magic is invalid (not a PS4 PKG)')
    # PS4 PKG content ID is a fixed 36-byte field starting at offset 0x40.
    # Compare the complete field; a renamed file cannot mask another title.
    if hdr[0x40:0x64] != content_id.encode('ascii'):
        raise ValueError('PKG header Content ID does not match the built app')
    if struct.unpack_from('>I', hdr, 0x0C)[0] == 0:
        raise ValueError('PKG header reports zero files')

    manifest = gp4.read_text(encoding='utf-8-sig')
    for required in ('eboot.bin', 'sce_sys/param.sfo', 'sce_sys/icon0.png',
                     'sce_sys/about/right.sprx', 'sce_module/libc.prx',
                     'sce_module/libSceFios2.prx'):
        if required not in manifest:
            raise ValueError('GP4 manifest missing ' + required)
    if jbc_mode == 'required' and 'sce_module/libjbc.sprx' not in manifest:
        raise ValueError('Installer GP4 manifest missing mandatory libjbc.sprx')
    if jbc_mode == 'forbidden' and 'sce_module/libjbc.sprx' in manifest:
        raise ValueError('DIAGNOSTIC GP4 manifest unexpectedly includes JBC')

    data = sfo.read_bytes()
    if data[:4] != b'\x00PSF':
        raise ValueError('SFO header is invalid')
    if title_id.encode('ascii') not in data or content_id.encode('ascii') not in data:
        raise ValueError('SFO does not contain expected Title ID and Content ID')
    h = hashlib.sha256()
    with pkg.open('rb') as inp:
        for block in iter(lambda: inp.read(1024 * 1024), b''):
            h.update(block)
    return {'file': str(pkg), 'bytes': pkg.stat().st_size, 'sha256': h.hexdigest(),
            'title_id': title_id, 'content_id': content_id, 'jbc_mode': jbc_mode}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pkg', required=True)
    ap.add_argument('--gp4', required=True)
    ap.add_argument('--sfo', required=True)
    ap.add_argument('--title-id', required=True)
    ap.add_argument('--content-id', required=True)
    ap.add_argument('--jbc', choices=['ignore', 'required', 'forbidden'], default='ignore')
    a = ap.parse_args()
    try:
        result = verify(a.pkg, a.gp4, a.sfo, a.title_id, a.content_id, a.jbc)
    except (OSError, ValueError, UnicodeError) as exc:
        print('PKG_VERIFICATION_FAILED:', exc, file=sys.stderr)
        return 1
    for k, v in result.items():
        print(k.upper() + ':', v)
    print('STRUCTURE_OK: Actual PKG produced; compatibility on PS4 still requires device test')
    return 0


if __name__ == '__main__':
    sys.exit(main())
