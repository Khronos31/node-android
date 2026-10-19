# Android Node.js 24 + N-API mock APK

**This is a minimal independent test APK, not EPGStation and not nodejs-mobile.**
It is deliberately kept outside the `dtv-android` application repo.

The same Java `ProcessBuilder` mechanism used in the first, manually tested
proof-of-concept loads `libnode_exec.so` from Android's `nativeLibraryDir`
and executes JavaScript from the app-private files directory. This iteration
adds a separately compiled **Node-API native addon**, allowing us to determine
whether `require("... .node")` succeeds with a standalone Android PIE Node.

## Test matrix

| Test button | Assertions | Expected marker |
| --- | --- | --- |
| Node --version | Native ARM executable can start | `v24.21.0` |
| Basic JS smoke | fs, SHA-256 crypto, local HTTP, child_process spawn | `NODE_BASIC_PASS` |
| Node-API addon | native `.node` load, N-API registration, C callback and value conversion | `NODE_ADDON_PASS` |

Each test shows stdout/stderr and its **exit code**. In particular, a failed
N-API test is useful evidence: Android's native dynamic linker may not expose
`napi_*` symbols from a standalone Node PIE to a dlopened addon. A successful
`node --version` alone does not prove addon compatibility.

## ABI and implementation

- Android API 24+, target SDK 34, armeabi-v7a and arm64-v8a
- Independent app ID: `dev.khronos31.nodeandroid.mock`
- No Android runtime dependencies beyond Android SDK and NDK; no JNI Node runtime
- Node binary staged as `lib/<abi>/libnode_exec.so`
- C addon staged as `lib/<abi>/libnapi_smoke.so`
- Java creates an app-private **symbolic link** `napi-smoke.node` to the
  executable-native-libraries directory; the addon itself remains in
  `nativeLibraryDir` (no `dlopen` from writable app data)
- `android:extractNativeLibs="true"` and legacy native lib packaging enabled
- A test-only Node build from **official Node.js v24.21.0** source is used to
  compile the Node-API addon, with official source SHA-256 verification.

## Build in GitHub Actions

[Build Android Node N-API Mock APK](../.github/workflows/mock-apk.yml)

The PR workflow uses a **reference runtime**: prebuilt Node 24.21.0 from
[Delusions6515/node-android-build](https://github.com/Delusions6515/node-android-build)
to verify the mock app and addon compilation. The exact archive SHA-256 is
hardcoded in [stage-runtime.py](scripts/stage-runtime.py). This reference mode
is a *scaffold test*, **not independent reproduction of Node.js**.

For the **actual Khronos31/node-android build**, after
[Build Node.js for Android](../.github/workflows/build.yml) has successfully
uploaded artifacts for **both** ABIs:

1. Open *Actions → Build Android Node N-API Mock APK → Run workflow*.
2. Select `runtime_source: run-artifacts` and enter that successful build's
   numeric GitHub Actions **run ID** in `runtime_run_id`.
3. The workflow fetches both ABI build artifacts using
   `actions/download-artifact`, verifies their embedded build metadata,
   SHA-256, ELF class and Android program interpreter.
4. It compiles the native N-API addon from official Node headers, creates
   the signed **debug** APK, and uploads it as a **workflow artifact only**.
5. Download the APK from that workflow's Artifacts section and install it.
   No release tag or update to `dtv-android` is performed.

Note that the workflow generated here is intentionally **manual** for
`run-artifacts` mode. It does not restart the long-running Node.js build,
nor download artifacts from an unfinished or failed run.

## Run locally (without HAOS dependencies)

On a Linux build host with Java 17, Android SDK/NDK
`27.0.12077973`, Gradle `7.6.4`, Python 3 and `readelf`:

```bash
export ANDROID_HOME=/path/to/android/sdk
export ANDROID_NDK_HOME="$ANDROID_HOME/ndk/27.0.12077973"

# Reference-only provisional Node.js binaries (checksum verified):
python3 mock-apk/scripts/stage-runtime.py --source reference
bash mock-apk/scripts/build-addon.sh
gradle -p mock-apk :app:assembleDebug
python3 mock-apk/scripts/verify-apk.py \
  mock-apk/app/build/outputs/apk/debug/app-debug.apk
```

This produces a debug-signed APK. It is not a production-signed Android build.

## On-device validation

```bash
adb install -r mock-apk/app/build/outputs/apk/debug/app-debug.apk
adb shell getprop ro.product.cpu.abi
adb shell getprop ro.build.version.sdk
adb logcat -d -s NodeMock:I AndroidRuntime:E linker:E
```

Open **Node 24 N-API Mock** on Android TV / Google TV or a phone, and press
all three test buttons. Save the full result of failed tests (including
`NODE_ADDON_LOAD_FAILED`, if present). Only the ABI of the current device
is actually exercised, even though the APK contains both.

For the first milestone, **do not** include EPGStation v3, sqlite3, CRC32,
background services, FFmpeg or tuner drivers. This tests the runtime and
module loader in isolation.

## Licensing

The app harness and C smoke addon are covered by this repository's MIT
license. The embedded Node runtime and Node headers come from Node's own
distribution; Node's official LICENSE, including third-party notices, is
packed in APK assets. Do not use the third-party reference binary for formal
releases without its own provenance/license verification.
