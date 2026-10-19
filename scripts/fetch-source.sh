#!/usr/bin/env bash
set -euo pipefail

repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
lock="$repo/versions/node-24.json"
work="${NODE_ANDROID_WORK_DIR:-$repo/.work}"
mkdir -p "$work"

readarray -t node_info < <(python3 - "$lock" <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text())
for key in ("version", "source_url", "sha256"):
    print(data[key])
PY
)
if (( ${#node_info[@]} != 3 )); then
  echo "Failed to read Node source version lock: $lock" >&2
  exit 2
fi
version="${node_info[0]}"
url="${node_info[1]}"
expected="${node_info[2]}"
archive="$work/node-v$version.tar.xz"
src="$work/node-v$version"

if [[ ! -s "$archive" ]]; then
  tmp="$(mktemp "$work/.node-download.XXXXXXXX")"
  trap 'rm -f "$tmp"' EXIT
  curl --fail --location --retry 3 --connect-timeout 15 --max-time 600 -o "$tmp" "$url"
  echo "$expected  $tmp" | sha256sum -c --status || {
    echo "ERROR: official Node.js source checksum mismatch" >&2
    exit 3
  }
  mv "$tmp" "$archive"
  trap - EXIT
fi
echo "$expected  $archive" | sha256sum -c --status || {
  echo "ERROR: existing source archive checksum mismatch: $archive" >&2
  exit 3
}
if [[ ! -d "$src" ]]; then
  tar -xf "$archive" -C "$work"
fi
test -f "$src/node.gyp"
echo "Verified Node.js v$version source: $src"
