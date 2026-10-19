#!/usr/bin/env bash
# Cross-compile EPGStation 3.0.0-beta2's real native dependencies for Android.
# The primary purpose is to expose toolchain/Node ABI incompatibilities.
# This does not build, start, or ship EPGStation itself.
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
abi="${1:?usage: build-android-native.sh <armeabi-v7a|arm64-v8a>}"
version="24.21.0"
ndk="${ANDROID_NDK_HOME:-${ANDROID_NDK_ROOT:-}}"
[[ -f "$ndk/source.properties" ]] || { echo "Android NDK is required" >&2; exit 2; }
ndk_version="$(sed -n 's/^Pkg.Revision *= *//p' "$ndk/source.properties")"
[[ "$ndk_version" == "27.0.12077973" ]] || {
  echo "Unexpected NDK: $ndk_version" >&2; exit 2;
}
case "$abi" in
  armeabi-v7a) target="armv7a-linux-androideabi24"; arch="arm"; cls="ELF32"; machine="ARM" ;;
  arm64-v8a) target="aarch64-linux-android24"; arch="arm64"; cls="ELF64"; machine="AArch64" ;;
  *) echo "Unsupported ABI: $abi" >&2; exit 2 ;;
esac

for command in node npm python3 readelf; do
  command -v "$command" >/dev/null || { echo "Missing $command" >&2; exit 2; }
done

# EPGStation manifest is fetched at a fixed upstream commit, not a moving tag.
# Check the exact native dependency versions before any compilation.
python3 "$root/verify-upstream.py" "$root/package.json"

if [[ ! -d "$root/node_modules" ]]; then
  (cd "$root" && npm install --ignore-scripts --no-audit --no-fund)
fi
gyp="$root/node_modules/.bin/node-gyp"
[[ -x "$gyp" ]] || { echo "node-gyp not installed" >&2; exit 3; }
mkdir -p "$root/.generated/gyp-dev"
"$gyp" install --target="$version" --devdir="$root/.generated/gyp-dev"

# node-gyp downloads the official Node 24.21.0 headers and uses the
# corresponding config.gypi, not the Linux host's default Node headers.
headers="$root/.generated/gyp-dev/$version"
test -f "$headers/include/node/node.h"
toolchain="$ndk/toolchains/llvm/prebuilt/linux-x86_64/bin"
export CC="$toolchain/${target}-clang"
export CXX="$toolchain/${target}-clang++"
export LINK="$CXX"
export AR="$toolchain/llvm-ar"
export GYP_DEFINES="target_arch=$arch v8_target_arch=$arch android_target_arch=$arch host_os=linux OS=android android_ndk_path=$ndk"
export GYP_CROSSCOMPILE=1
export npm_config_build_from_source=true
output="$root/.generated/output/$abi"
mkdir -p "$output"
for module in better-sqlite3 fs-ext diskusage-ng; do
  dir="$root/node_modules/$module"
  [[ -d "$dir" ]] || { echo "Missing installed package: $module" >&2; exit 4; }
  license="$(find "$dir" -maxdepth 1 -type f \\( -iname 'license' -o -iname 'license.*' \\) -print -quit)"
  if [[ -n "$license" ]]; then
    cp "$license" "$output/$module.LICENSE"
  fi
  if [[ ! -f "$dir/binding.gyp" ]]; then
    echo "NO_BINDING_GYP $module: review package-specific build metadata" | tee "$output/$module.NO_BINDING_GYP"
    continue
  fi
  echo "::group::Build $module for $abi (Node $version)"
  (cd "$dir" && "$gyp" rebuild --release --arch="$arch" --nodedir="$headers" --jobs=3)
  echo "::endgroup::"
  count=0
  while IFS= read -r -d '' addon; do
    dest="$output/${module}--$(basename "$addon")"
    cp "$addon" "$dest"
    head="$(readelf -h "$dest")"
    [[ "$head" == *"Class:"*"$cls"* && "$head" == *"Machine:"*"$machine"* ]] || {
      echo "Incorrect ELF ABI for $module: $dest" >&2; exit 5;
    }
    echo "NATIVE_ADDON_BUILT $abi $module $dest"
    count=$((count + 1))
  done < <(find "$dir/build/Release" -type f -name '*.node' -print0)
  (( count > 0 )) || { echo "No .node output for $module" >&2; exit 5; }
done

python3 "$root/verify-output.py" "$output" "$abi"
