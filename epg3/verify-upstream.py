#!/usr/bin/env python3
"""Check a pinned EPGStation v3 manifest against our native dependency probe."""
import json
import sys
import urllib.request
from pathlib import Path

REPO_COMMIT = "1793ab74088be8791d191c9621ab881e50741119"
VERSION = "3.0.0-beta2"
NAMES = ("better-sqlite3", "fs-ext", "diskusage-ng")

def verify(upstream, local):
    if upstream.get("version") != VERSION:
        raise RuntimeError("EPGStation version changed at the pinned commit")
    if upstream.get("engines", {}).get("node") != ">=24":
        raise RuntimeError("EPGStation Node requirement changed")
    for package in NAMES:
        wanted = upstream.get("dependencies", {}).get(package)
        actual = local.get("dependencies", {}).get(package)
        if not wanted or actual != wanted:
            raise RuntimeError(f"Native dependency drift: {package}: upstream={wanted!r}, probe={actual!r}")
    return True

if __name__ == "__main__":
    manifest = json.loads(Path(sys.argv[1]).read_text())
    url = f"https://raw.githubusercontent.com/l3tnun/EPGStation/{REPO_COMMIT}/package.json"
    with urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "node-android-epg3-dep-probe"}),
        timeout=30,
    ) as data:
        upstream = json.loads(data.read(256_000))
    verify(upstream, manifest)
    print("EPGSTATION_MANIFEST_PIN_OK version=" + VERSION)
