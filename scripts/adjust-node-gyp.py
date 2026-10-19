#!/usr/bin/env python3
"""Constrain a one-line Android libatomic fix to the pinned Node source."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: adjust-node-gyp.py /path/to/node-source")

target = Path(sys.argv[1]) / "node.gyp"
content = target.read_text(encoding="utf-8")
old = """['OS=="linux" and clang==1', {"""
new = """['(OS=="linux" or OS=="android") and clang==1', {"""
if content.count(old) == 1 and new not in content:
    target.write_text(content.replace(old, new, 1), encoding="utf-8")
    print("Enabled Android libatomic link condition in node.gyp")
elif content.count(new) == 1 and old not in content:
    print("Android libatomic link condition already applied")
else:
    raise SystemExit("ERROR: Node gyp libatomic condition changed unexpectedly")
