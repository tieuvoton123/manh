#!/usr/bin/env python3
"""Obtain pinned stb_truetype.h; replace old/test stubs only after SHA verification.

The repository may still contain a tiny syntax-only stub from earlier releases.
Never accept that stub as the production renderer. On CI we fetch the actual
stb_truetype.h from a fixed GitHub commit, verify its Git blob SHA-1, and
atomically publish it. A locally cached authentic file is safe to reuse.
"""
from pathlib import Path
import hashlib
import tempfile
from urllib.request import urlopen

COMMIT = "2c980bb59875b0d32144a71867fbdebb2f77cd20"
BLOB = "90a5c2e2b3fe563c98585294ca7a949876aec94c"
URL = "https://raw.githubusercontent.com/nothings/stb/" + COMMIT + "/stb_truetype.h"
MAX_BYTES = 300000
path = Path(__file__).resolve().parent / "stb_truetype.h"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def main() -> None:
    if path.is_file() and git_blob_sha(path.read_bytes()) == BLOB:
        print("Verified cached stb_truetype.h:", BLOB)
        return

    if path.exists():
        print("Replacing stale/test-only stb_truetype.h with verified upstream release")
    try:
        with urlopen(URL, timeout=35) as response:
            data = response.read(MAX_BYTES + 1)
    except Exception as exc:
        raise SystemExit("Cannot download pinned stb_truetype.h; check GitHub access: " + str(exc)) from exc

    actual = git_blob_sha(data)
    if actual != BLOB:
        raise SystemExit("Mismatch stb_truetype.h, got " + actual + "; expected " + BLOB)

    # Atomic replacement: do not overwrite a working header if writing fails.
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", prefix=".stb-", suffix=".tmp",
                                         dir=str(path.parent), delete=False) as fp:
            tmp_path = Path(fp.name)
            fp.write(data)
        tmp_path.replace(path)
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()
    print("Pinned stb_truetype.h verified:", actual)


if __name__ == "__main__":
    main()
