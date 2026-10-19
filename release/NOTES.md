# Node.js 24.21.0 for Android — first binary candidate

Standalone Node.js runtime built from pinned official Node.js 24.21.0 source
and Khronos31/node-android compatibility patches.

**Pre-release:** both `armeabi-v7a` and `arm64-v8a` passed Android
device tests with our earlier own-source-build binaries (Node process startup,
basic JS functions, Node-API and V8 addons, and selected EPGStation 3 beta2
dependencies). The actual `-j4`/ccache-enabled binary archives promoted from
[successful build 39240791051](https://github.com/Khronos31/node-android/actions/runs/39240791051)
passed CI/ELF checks; those precise binaries have **not** been retested
byte-for-byte on Android devices.

Choose the archive matching your Android ABI:
`node-v24.21.0-android-armeabi-v7a.tar.xz` or
`node-v24.21.0-android-arm64-v8a.tar.xz`. Check against
`SHA256SUMS`. `RELEASE-METADATA.json` records the original source digest,
patches, build run and release commit.

Each archive includes `bin/node`, `LICENSE`, `BUILD-METADATA.json`,
and its internal `SHA256SUMS`.

**Android packaging:** `bin/node` is a PIE **executable**, not JNI
`libnode.so`. In an APK it can be renamed to
`jniLibs/<abi>/libnode_exec.so`, extracted to
`ApplicationInfo.nativeLibraryDir`, then launched via
`ProcessBuilder`. Do not execute unpacked binaries from the app's
writable `filesDir` on modern Android.

The runtime does not include npm or EPGStation. Complete EPGStation 3 startup
and mirakc integration are **not** covered by these release checks.
