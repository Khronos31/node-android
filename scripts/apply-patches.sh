#!/usr/bin/env bash
set -euo pipefail

repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
src="${1:?usage: apply-patches.sh /path/to/node-source}"
[[ -f "$src/node.gyp" ]] || { echo "Missing official Node source: $src" >&2; exit 2; }
shopt -s nullglob
patches=("$repo"/patches/node-24/*.patch)
(( ${#patches[@]} > 0 )) || { echo "No patches selected" >&2; exit 2; }

for p in "${patches[@]}"; do
  echo "Checking $(basename "$p")"
  if patch -d "$src" -p1 --fuzz=0 --batch --forward --dry-run -i "$p" >/dev/null 2>&1; then
    patch -d "$src" -p1 --fuzz=0 --batch --forward --no-backup-if-mismatch -i "$p"
  elif patch -d "$src" -p1 --fuzz=0 --batch --reverse --dry-run -i "$p" >/dev/null 2>&1; then
    echo "  already applied; no change"
  else
    echo "ERROR: patch does not match Node source: $p" >&2
    exit 3
  fi
done
