#!/usr/bin/env bash
set -euo pipefail

repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
src="${1:?usage: prepare-host-llvm.sh /path/to/node-source /path/to/work}"
work="${2:?usage: prepare-host-llvm.sh /path/to/node-source /path/to/work}"
deps="$src/deps/v8/DEPS"
[[ -f "$deps" ]] || { echo "Missing V8 DEPS: $deps" >&2; exit 2; }

readarray -t llvm_info < <(python3 - "$deps" <<'PY'
import re, sys
from pathlib import Path
data = Path(sys.argv[1]).read_text(encoding="utf-8")
pattern = re.compile(
    r"""['"]object_name['"]:\s*['"](Linux_x64/clang-llvmorg[^'"]+\.tar\.xz)['"]\s*,\s*['"]sha256sum['"]:\s*['"]([a-f0-9]{64})"""
)
result = pattern.search(data)
if not result:
    raise SystemExit("V8 DEPS contains no recognizable pinned Linux x64 LLVM binary")
print(result.group(1))
print(result.group(2))
PY
)
(( ${#llvm_info[@]} == 2 )) || { echo "Unable to parse V8 LLVM pin" >&2; exit 3; }
object="${llvm_info[0]}"
checksum="${llvm_info[1]}"
host="$work/llvm-host"
if [[ -x "$host/bin/clang" ]]; then
  echo "$host"
  exit 0
fi

mkdir -p "$work"
archive="$work/$(basename "$object")"
if [[ ! -f "$archive" ]]; then
  tmp="$(mktemp "$work/.host-llvm.XXXXXXXX")"
  trap 'rm -f "$tmp"' EXIT
  curl --fail --location --retry 3 --connect-timeout 15 --max-time 900 \
    -o "$tmp" "https://commondatastorage.googleapis.com/chromium-browser-clang/$object"
  echo "$checksum  $tmp" | sha256sum -c --status || {
    echo "ERROR: V8 host LLVM SHA-256 mismatch" >&2; exit 4;
  }
  mv "$tmp" "$archive"
  trap - EXIT
fi
echo "$checksum  $archive" | sha256sum -c --status || {
  echo "ERROR: cached V8 host LLVM SHA-256 mismatch" >&2; exit 4;
}
mkdir -p "$host"
tar -xf "$archive" -C "$host"
[[ -x "$host/bin/clang" ]] || { echo "Host LLVM archive has no clang" >&2; exit 5; }
echo "$host"
