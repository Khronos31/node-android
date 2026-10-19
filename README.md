# node-android

Build a **standalone Node.js runtime for Android** from pinned official Node.js
sources, with a small, inspectable Android compatibility patch set.

This repository is independent of both Node.js upstream and the Android
application [dtv-android](https://github.com/Khronos31/dtv-android). No
`nodejs-mobile` framework or Termux installation is required at runtime.

> **State:** Own-source-built Node.js 24.21.0 has passed real Android device
> tests on **both** ABIs: standalone process, basic JS, N-API and V8 addons,
> and selected EPGStation 3 beta2 package functions. The final ccache/-j4
> binaries have passed build/ELF CI but not byte-for-byte device retesting;
> the first permanent GitHub binary release is therefore a **pre-release**.

## Build target

| Property | Pinned initial value |
| --- | --- |
| Node.js | 24.21.0 (24.x) |
| Android | API 24+ |
| ABIs | `armeabi-v7a`, `arm64-v8a` |
| Android NDK | 27.0.12077973 |
| Dependency model | bundled OpenSSL, ICU, zlib, libuv (`--partly-static`) |
| Host | Linux x86_64 with Python 3, Bash, Ninja, Clang, 32-bit host libraries |

Source URI and SHA-256, NDK version, ABI mappings are in
[`versions/node-24.json`](versions/node-24.json).

## Build

On a Linux host with Android NDK installed, Ninja, `curl`, `patch`, `tar`,
`readelf`, Python 3, and host multiarch development libraries:

```bash
export ANDROID_NDK_HOME=/path/to/android-ndk-r27
./scripts/build.sh arm64-v8a
./scripts/build.sh armeabi-v7a
```

Building a single architecture creates
`dist/node-v24.21.0-android-<abi>.tar.xz`. Compiled artifacts are kept outside
Git. The script obtains the **pinned host LLVM** toolchain described in Node's
V8 DEPS (with SHA-256 verification) because normal distro compilers may not
support V8's current host build. Two ABIs are built in independent work
directories. The build fails on a patch that no longer applies.

You can also run the
[Build Node.js for Android](.github/workflows/build.yml) GitHub Actions workflow
through `workflow_dispatch` (or by opening a pull request); it compiles and
uploads both ABI archives as **workflow artifacts**, not GitHub Releases.
Binary releases are promoted through a separate, tag-gated
[release workflow](.github/workflows/release.yml), which verifies both CI
archives, source and patch hashes, and release provenance without rebuilding
Node. See [Binary releases](docs/releases.md).

## Package contract

The archive contains a native PIE ELF executable at `bin/node`,
`LICENSE` (from official Node source), build metadata, and SHA-256 checksums.
The executable is intended to be renamed to e.g.
`libnode_exec.so` inside `app/src/main/jniLibs/<abi>/`, then executed from
Android's `ApplicationInfo.nativeLibraryDir` using `ProcessBuilder`.
Do **not** copy executable files to writable Android `filesDir` and try to
execute them on modern Android.

Consumers such as `dtv-android` should download a pinned, versioned
[GitHub Release](https://github.com/Khronos31/node-android/releases),
verify its published `SHA256SUMS` and keep Node's `LICENSE`.

After verifying each ABI on actual devices, `dtv-android` should consume a
fixed-version archive with SHA-256 verification. APK generation, EPGStation,
native addon builds and lifecycle supervision stay in `dtv-android`.

## Tests / constraints

- GitHub Actions runs shell/source/patch validation and both cross-builds.
- The build checks Android PIE ABI/interpreter and bundled dependency linkage.
- The JS script at [`tests/smoke.js`](tests/smoke.js) is for on-device testing.
- Passing ELF checks **does not** confirm on-device JIT, `dlopen` of native
  Node addons, V8 snapshots, lifecycle behavior, or EPGStation v3 compatibility.
- **Verified on real devices (both ABIs):** our own Node 24.21.0 runtime,
  basic JS, Node-API, V8-native addons, SQLite/WAL/locking, `aribts` CRC32
  and `diskusage-ng` capacity lookup.
- **Not yet verified:** complete EPGStation 3 boot, database migration,
  lifecycle supervision or mirakc/recording integration; individual
  ccache/-j4 release archive bytes have not had separate on-device retesting.

See [patch-policy](docs/patch-policy.md) for patch licensing and provenance.

## License

Custom scripts are MIT-licensed (see `LICENSE`). Node.js source is separately
licensed (MIT and bundled third-party licenses); patched upstream components
retain applicable upstream licenses. Distribute Node's official `LICENSE`
alongside all binaries.

## 16 KiB memory-page ELF layout

Android 15+ devices may use 16 KiB memory pages. The standalone Node ELF
and native test addons must have **all** `PT_LOAD` segments aligned at least
16 KiB, with congruent offsets and virtual addresses. The build scripts
supply explicit linker flags for the **target** GYP/Ninja binaries on NDK
r27, and `scripts/validate_elf_pages.py` fails CI on any violating segment.
The separately built EPGStation 3 native modules must apply the same target
linker flags and pass the same ELF gate.

This static ELF test is **not** proof of full runtime correctness on a real
16 KiB-page device: runtime mmap/snapshot behavior and Android system
compatibility mode must be exercised separately. Existing tag
`v24.21.0-android.1` is not changed; a fixed build requires a new release.
