#!/usr/bin/env bash
set -euo pipefail

repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
abi="${1:?usage: build.sh <armeabi-v7a|arm64-v8a>}"
[[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]] || {
  echo "Currently supported build host: Linux x86_64" >&2; exit 2;
}
case "$abi" in
  armeabi-v7a) arch=arm; prefix=armv7a-linux-androideabi; host_m32=" -m32" ;;
  arm64-v8a)  arch=arm64; prefix=aarch64-linux-android; host_m32="" ;;
  *) echo "Unsupported ABI: $abi" >&2; exit 2 ;;
esac

readarray -t lock < <(python3 - "$repo/versions/node-24.json" <<'PY'
import json, sys
data=json.load(open(sys.argv[1]))
for key in ('version', 'android_api', 'ndk_version'):
    print(data[key])
PY
)
(( ${#lock[@]} == 3 )) || { echo "Invalid Node version lock" >&2; exit 2; }
version="${lock[0]}"
api="${lock[1]}"
ndk_version="${lock[2]}"
work="${NODE_ANDROID_WORK_DIR:-$repo/.work/$abi}"
dist="${NODE_ANDROID_DIST_DIR:-$repo/dist}"
ndk="${ANDROID_NDK_HOME:-${ANDROID_NDK_ROOT:-}}"
[[ -n "$ndk" && -d "$ndk" ]] || {
  echo "Set ANDROID_NDK_HOME to Android NDK $ndk_version" >&2; exit 2;
}
actual_ndk="$(sed -n 's/^Pkg.Revision *= *//p' "$ndk/source.properties")"
[[ "$actual_ndk" == "$ndk_version" ]] || {
  echo "Expected Android NDK $ndk_version, found $actual_ndk" >&2; exit 2;
}
toolchain="$ndk/toolchains/llvm/prebuilt/linux-x86_64/bin"
[[ -x "$toolchain/${prefix}${api}-clang" ]] || {
  echo "NDK compiler not found" >&2; exit 2;
}
for cmd in curl tar patch sha256sum ninja readelf python3; do
  command -v "$cmd" >/dev/null || { echo "Missing required tool: $cmd" >&2; exit 2; }
done

mkdir -p "$work" "$dist"
NODE_ANDROID_WORK_DIR="$work" "$repo/scripts/fetch-source.sh"
src="$work/node-v$version"
"$repo/scripts/apply-patches.sh" "$src"
python3 "$repo/scripts/adjust-node-gyp.py" "$src"
llvm_host="$("$repo/scripts/prepare-host-llvm.sh" "$src" "$work")"
[[ -x "$llvm_host/bin/clang++" ]] || { echo "Missing V8 host clang++" >&2; exit 3; }

export CC="$toolchain/${prefix}${api}-clang"
export CXX="$toolchain/${prefix}${api}-clang++"
export AR="$toolchain/llvm-ar"
export CC_host="$llvm_host/bin/clang$host_m32"
export CXX_host="$llvm_host/bin/clang++$host_m32"
export LINK_host="$llvm_host/bin/clang++$host_m32"
export PATH="$toolchain:$PATH"
export GYP_DEFINES="target_arch=$arch v8_target_arch=$arch android_target_arch=$arch host_os=linux OS=android android_ndk_path=$ndk"

# CI cache acceleration: optionally wrap both the Android NDK target compiler
# and V8's pinned host LLVM compiler with ccache. Leave this opt-in to avoid
# altering local builds, and let ccache validate compiler/input changes.
# Do not attempt to cache ABI-dependent Ninja objects from another target.
if [[ "${NODE_ANDROID_USE_CCACHE:-0}" == "1" ]]; then
  command -v ccache >/dev/null || {
    echo "NODE_ANDROID_USE_CCACHE=1 requires ccache in PATH" >&2; exit 2;
  }
  export CCACHE_DIR="${CCACHE_DIR:-$repo/.ccache/$abi}"
  export CCACHE_BASEDIR="${CCACHE_BASEDIR:-$repo}"
  export CCACHE_COMPILERCHECK="${CCACHE_COMPILERCHECK:-content}"
  export CCACHE_COMPRESS="${CCACHE_COMPRESS:-true}"
  export CCACHE_MAXSIZE="${CCACHE_MAXSIZE:-1500M}"
  mkdir -p "$CCACHE_DIR"
  export CC="ccache $CC"
  export CXX="ccache $CXX"
  export CC_host="ccache $CC_host"
  export CXX_host="ccache $CXX_host"
  export LINK_host="$llvm_host/bin/clang++$host_m32"
  echo "ccache enabled: $CCACHE_DIR (ABI $abi; limit $CCACHE_MAXSIZE)"
fi
export CFLAGS="${CFLAGS:-} -I$repo/patches/stubs"
# Android API 24-27 lacks aligned_alloc; Node's cctest path uses it.
if (( api < 28 )); then
  export CFLAGS="$CFLAGS -Daligned_alloc=memalign"
fi
# GYP's Ninja target toolset reads LDFLAGS; LDFLAGS_host is independent.
# NDK r27 needs explicit target linker flags for 16 KiB PT_LOAD alignment.
# Keep the host LLVM/V8 generators' link settings unchanged.
export LDFLAGS="${LDFLAGS:-} -Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384"
jobs="${NODE_ANDROID_JOBS:-4}"
[[ "$jobs" =~ ^[1-9][0-9]*$ ]] || { echo "NODE_ANDROID_JOBS must be positive integer" >&2; exit 2; }

echo "Building official Node.js v$version for $abi (API $api, NDK $ndk_version, jobs=$jobs)"
cd "$src"
./configure --dest-cpu="$arch" --dest-os=android \
  --openssl-no-asm --cross-compiling --partly-static \
  --with-intl=full-icu --without-npm --ninja
# Only build the Node runtime; avoid the cctest target and its host-tool issues.
ninja -C out/Release -j "$jobs" node

binary="$src/out/Release/node"
[[ -f "$binary" ]] || { echo "Node binary missing: $binary" >&2; exit 4; }
stage="$work/stage"
rm -rf "$stage"
mkdir -p "$stage/bin"
cp "$binary" "$stage/bin/node"
"$toolchain/llvm-strip" --strip-unneeded "$stage/bin/node"
cp "$src/LICENSE" "$stage/LICENSE"

python3 "$repo/scripts/inspect-elf.py" "$stage/bin/node" "$abi"
python3 - "$repo" "$stage" "$abi" "$ndk_version" <<'PY'
import hashlib, json, os, sys
from pathlib import Path
repo, stage, abi, ndk = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
lock = json.loads((repo / 'versions/node-24.json').read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
patches = sorted((repo / 'patches/node-24').glob('*.patch'))
meta = {
    'node_version': lock['version'],
    'source_url': lock['source_url'],
    'source_sha256': lock['sha256'],
    'android_api': lock['android_api'],
    'android_abi': abi,
    'ndk_version': ndk,
    'binary_sha256': sha(stage / 'bin/node'),
    'host': 'linux-x86_64',
    'patch_sha256': {p.name: sha(p) for p in patches},
    'source_repo': os.environ.get('GITHUB_REPOSITORY', 'Khronos31/node-android'),
    'source_commit': os.environ.get('GITHUB_SHA', 'local-build'),
}
(stage / 'BUILD-METADATA.json').write_text(json.dumps(meta, indent=2, sort_keys=True)+'\n')
files = ('bin/node', 'LICENSE', 'BUILD-METADATA.json')
(stage / 'SHA256SUMS').write_text(''.join(
    f"{sha(stage / f)}  {f}\n" for f in files
))
PY

artifact="$dist/node-v$version-android-$abi.tar.xz"
tar --sort=name --owner=0 --group=0 --numeric-owner -cJf "$artifact" -C "$stage" .
echo "Created: $artifact"
sha256sum "$artifact"
