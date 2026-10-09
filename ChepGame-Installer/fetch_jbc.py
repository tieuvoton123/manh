#!/usr/bin/env python3
"""Retrieve a pinned, integrity-checked PS4-IPI JBC module for personal builds.

Existing local assets are never silently replaced.  This does NOT establish
runtime compatibility on a particular firmware; verify on a test PS4 first.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from urllib import request

# Upstream PS4-IPI (0x199), commit from the repository's main branch on 2026-10-09.
UPSTREAM_REPO = "0x199/ps4-ipi"
PINNED_COMMIT = "687fb0ea675994f8bc9f2dc2b0ce1ca82e8092e0"
EXPECTED_BLOB_SHA = "281946bfa3803426da3a48e78f647349400986f9"
EXPECTED_SIZE = 9952
REMOTE_PATH = "pkg/sce_module/libjbc.sprx"
SELF_MAGIC = bytes.fromhex("4f153d1d")  # PS4 SELF header, not a normal ELF file.
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "assets" / "libjbc.sprx"


def git_blob_sha(data):
    blob = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(blob).hexdigest()


def validate_self(data):
    if len(data) < 4096 or data[:4] != SELF_MAGIC:
        raise ValueError("Not a PS4 SELF/SPRX (unexpected header/size)")


def validate_upstream(data):
    validate_self(data)
    if len(data) != EXPECTED_SIZE:
        raise ValueError("Upstream libjbc.sprx size mismatch")
    if git_blob_sha(data) != EXPECTED_BLOB_SHA:
        raise ValueError("Upstream libjbc.sprx Git blob checksum mismatch")


def read_url(url):
    req = request.Request(url, headers={"User-Agent": "ChepGame-Installer-JBC-Fetch/0.3.1"})
    with request.urlopen(req, timeout=25) as response:
        return response.read(256 * 1024 + 1)


def download_pinned():
    raw_url = ("https://raw.githubusercontent.com/" + UPSTREAM_REPO + "/" +
               PINNED_COMMIT + "/" + REMOTE_PATH)
    errors = []
    for attempt in range(3):
        try:
            data = read_url(raw_url)
            validate_upstream(data)
            return data
        except Exception as exc:
            errors.append(f"raw attempt {attempt + 1}: {exc}")
            if attempt < 2:
                time.sleep(attempt + 1)
    # API fallback: Git blob endpoint returns JSON/base64; verify again.
    url = ("https://api.github.com/repos/" + UPSTREAM_REPO +
           "/git/blobs/" + EXPECTED_BLOB_SHA)
    try:
        result = json.loads(read_url(url).decode("utf-8"))
        if result.get("encoding") != "base64":
            raise ValueError("Unexpected GitHub blob encoding")
        data = base64.b64decode(result["content"], validate=False)
        validate_upstream(data)
        return data
    except Exception as exc:
        errors.append(f"API fallback: {exc}")
    raise RuntimeError("Failed to fetch verified upstream JBC: " + "; ".join(errors))


def install(output, diagnostic_only=False):
    output = Path(output)
    # Explicit diagnostic mode takes precedence over an existing local module.
    # Packaging must additionally pass DIAGNOSTIC_ONLY=1 to make, so it is
    # impossible to accidentally include a privilege module in a UI-only PKG.
    if diagnostic_only:
        print("DIAGNOSTIC_ONLY: JBC disabled even if a local module is present; cannot install PKGs")
        return "diagnostic"
    if output.exists():
        existing = output.read_bytes()
        validate_self(existing)
        print("LOCAL_JBC_VALID_FORMAT", output, hashlib.sha256(existing).hexdigest())
        print("NOTE: Local file export/firmware compatibility cannot be proved offline")
        return "local"
    data = download_pinned()
    validate_upstream(data)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(prefix="libjbc-", suffix=".tmp", dir=output.parent,
                                         delete=False) as f:
            temp = Path(f.name)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        # Refuse to overwrite a module introduced by another process.
        if output.exists():
            raise FileExistsError(f"JBC appeared while downloading: {output}")
        os.replace(temp, output)
        temp = None
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    print("UPSTREAM_JBC_VERIFIED", output, len(data), git_blob_sha(data))
    print("SOURCE", "https://github.com/" + UPSTREAM_REPO + "/blob/" + PINNED_COMMIT + "/" + REMOTE_PATH)
    print("CAUTION: upstream binary NOT YET validated on your GoldHEN 2.4b18.9 PS4")
    return "downloaded"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--diagnostic-only", action="store_true")
    args = ap.parse_args(argv)
    try:
        install(args.output, args.diagnostic_only)
    except (OSError, ValueError, RuntimeError) as exc:
        print("JBC_SETUP_FAILED:", exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
