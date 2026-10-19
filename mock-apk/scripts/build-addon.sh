#!/usr/bin/env bash
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ndk="${ANDROID_NDK_HOME:-${ANDROID_NDK_ROOT:-}}"
[[ -f "$ndk/source.properties" ]] || {
  echo "ANDROID_NDK_HOME must point to NDK 27.0.12077973" >&2; exit 2;
}
ndk_version="$(sed -n 's/^Pkg.Revision *= *//p' "$ndk/source.properties")"
[[ "$ndk_version" == "27.0.12077973" ]] || {
  echo "NDK mismatch: expected 27.0.12077973, found $ndk_version" >&2; exit 2;
}
toolchain="$ndk/toolchains/llvm/prebuilt/linux-x86_64/bin"
[[ -x "$toolchain/clang" ]] || { echo "Missing Android NDK clang" >&2; exit 2; }

python3 "$root/scripts/fetch-headers.py"
for spec in \
  "armeabi-v7a:armv7a-linux-androideabi24:ELF32:ARM" \
  "arm64-v8a:aarch64-linux-android24:ELF64:AArch64"; do
    IFS=: read -r abi target cls machine <<< "$spec"
    dst="$root/.generated/jniLibs/$abi/libnapi_smoke.so"
    mkdir -p "$(dirname "$dst")"
    "$toolchain/clang" --target="$target" \
      -std=c11 -O2 -Wall -Wextra -Werror -fPIC -fvisibility=hidden -shared \
      -Wl,-soname,libnapi_smoke.so \
      -I"$root/.generated/node-headers" \
      "$root/tests/native-addon/addon.c" -o "$dst"

    head="$(readelf -h "$dst")"
    [[ "$head" == *"Class:"*"$cls"* ]] || { echo "Wrong ELF class: $abi" >&2; exit 3; }
    [[ "$head" == *"Machine:"*"$machine"* ]] || { echo "Wrong ELF machine: $abi" >&2; exit 3; }
    readelf -W --dyn-syms "$dst" | grep -q "napi_register_module_v1" || {
      echo "Native addon registration symbol missing: $abi" >&2; exit 3;
    }
    readelf -W --dyn-syms "$dst" | grep -q "napi_create_function" || {
      echo "Expected unresolved Node-API import missing: $abi" >&2; exit 3;
    }
    echo "ADDON_OK $abi: $(sha256sum "$dst")"
done
