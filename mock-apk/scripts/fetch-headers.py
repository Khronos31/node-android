#!/usr/bin/env python3
"""Fetch official Node v24.21.0 N-API headers from verified source, not Termux."""
import hashlib
import shutil
import tarfile
import urllib.request
from pathlib import Path

VERSION = "24.21.0"
SOURCE_SHA = "a6f54defb6fd7c84f41dba13d61e78e9b4e0961712cf61f29715c05f5ced94fc"
HEADERS = [
    "node_api.h", "node_api_types.h",
    "js_native_api.h", "js_native_api_types.h"
]

def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

root = Path(__file__).resolve().parents[1]
generated = root / ".generated"
archive = generated / "download-cache" / f"node-v{VERSION}.tar.xz"
headers = generated / "node-headers"
archive.parent.mkdir(parents=True, exist_ok=True)
headers.mkdir(parents=True, exist_ok=True)

if not archive.is_file():
    url = f"https://nodejs.org/dist/v{VERSION}/node-v{VERSION}.tar.xz"
    tmp = archive.with_suffix(archive.suffix + ".part")
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent":"Khronos31-node-android-mock/0.2"})
        with urllib.request.urlopen(request, timeout=90) as src, open(tmp, "wb") as dst:
            shutil.copyfileobj(src, dst)
        if digest(tmp) != SOURCE_SHA:
            raise RuntimeError("Official Node source SHA-256 mismatch")
        tmp.replace(archive)
    finally:
        tmp.unlink(missing_ok=True)
if digest(archive) != SOURCE_SHA:
    raise RuntimeError("Cached official Node source SHA-256 mismatch")

with tarfile.open(archive, "r:xz") as tf:
    for name in HEADERS:
        member = tf.getmember(f"node-v{VERSION}/src/{name}")
        if not member.isfile():
            raise RuntimeError("Node header is not a regular file: " + name)
        with tf.extractfile(member) as src, open(headers / name, "wb") as dst:
            shutil.copyfileobj(src, dst)
        print("HEADER:", name)

    # Include the complete official Node LICENSE and bundled dependency notices
    # in the APK even for prebuilt reference-mode Node binaries.
    license_member = tf.getmember(f"node-v{VERSION}/LICENSE")
    licenses = generated / "assets" / "licenses"
    licenses.mkdir(parents=True, exist_ok=True)
    with tf.extractfile(license_member) as source, open(licenses / "Node-LICENSE", "wb") as out:
        shutil.copyfileobj(source, out)
print("Official Node headers and LICENSE verified, directory:", headers)
