# node-android

Build a **standalone Node.js runtime for Android** from pinned official Node.js
sources, with a small, inspectable Android compatibility patch set.

This repository is independent of both Node.js upstream and the Android
application [dtv-android](https://github.com/Khronos31/dtv-android). No
`nodejs-mobile` framework or Termux installation is required at runtime.

> **State:** First implementation / validation pending. Source download,
> patching, cross-build scripts and CI are provided. Do **not** treat an
> untested CI output as a supported binary release. The previous smoke-tested
> APK used third-party prebuilt Node 24.21.0, not this repository's output.

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
No automatic release is performed before runtime testing.

## Package contract

The archive contains a native PIE ELF executable at `bin/node`,
`LICENSE` (from official Node source), build metadata, and SHA-256 checksums.
The executable is intended to be renamed to e.g.
`libnode_exec.so` inside `app/src/main/jniLibs/<abi>/`, then executed from
Android's `ApplicationInfo.nativeLibraryDir` using `ProcessBuilder`.
Do **not** copy executable files to writable Android `filesDir` and try to
execute them on modern Android.

After verifying each ABI on actual devices, `dtv-android` should consume a
fixed-version archive with SHA-256 verification. APK generation, EPGStation,
native addon builds and lifecycle supervision stay in `dtv-android`.

## Tests / constraints

- GitHub Actions runs shell/source/patch validation and both cross-builds.
- The build checks Android PIE ABI/interpreter and bundled dependency linkage.
- The JS script at [`tests/smoke.js`](tests/smoke.js) is for on-device testing.
- Passing ELF checks **does not** confirm on-device JIT, `dlopen` of native
  Node addons, V8 snapshots, lifecycle behavior, or EPGStation v3 compatibility.
- First milestone: reproduce the working Node.js 24.21.0 mock with our own
  independently compiled binaries, then compare both ABIs on devices.

See [patch-policy](docs/patch-policy.md) for patch licensing and provenance.

## License

Custom scripts are MIT-licensed (see `LICENSE`). Node.js source is separately
licensed (MIT and bundled third-party licenses); patched upstream components
retain applicable upstream licenses. Distribute Node's official `LICENSE`
alongside all binaries.
