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

Each test shows stdout/stderr and its **exit code**. The addon test also
prints `addon.realpath` and `addon.resolved`; the latter **must end in
`.node`**. If it ends in `.so`, a `SyntaxError` is a module resolution error,
not evidence of missing N-API exports. In particular, a failed
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
- The addon test passes **`--preserve-symlinks`** before the JS entry point.
  Otherwise Node's CommonJS resolver canonicalizes the symlink to
  `libnapi_smoke.so` and tries to parse the ELF as JavaScript instead of
  invoking the `.node` native addon loader
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

## Test our own Node.js build without merging either PR

GitHub Actions' `workflow_dispatch` trigger only works for workflows that
already exist on the **default branch**. Because this workflow currently lives
only in a draft PR, using *Run workflow* in the Actions UI is **not yet possible**.

Instead, the PR workflow reads [`runtime-selection.json`](runtime-selection.json).
Its default `reference` mode produces the already-tested reference-based APK.

Once [Build Node.js for Android](../.github/workflows/build.yml) finishes
successfully **and uploads both ABI artifacts**, change the file on the
`feat/napi-mock-harness` branch to:

```json
{
  "source": "run-artifacts",
  "runtime_run_id": 39220534794
}
```

The run ID above refers to the **current build attempt**. Only select it if that
run ends successfully; use a new successful run ID if it fails. Committing the
selection file automatically triggers this PR's short APK build without
restarting the expensive Node.js cross-compile.

The mock APK workflow first verifies the selected run completed successfully
under `Khronos31/node-android`, then downloads **both** ABI artifacts using
`actions/download-artifact`, and verifies source version, binary hashes,
ELF headers and build metadata before assembling and uploading a debug-signed
APK. It does not publish a GitHub Release or modify `dtv-android`.

**After** this workflow has been merged into `main`, the original manual
`workflow_dispatch` inputs (`runtime_source: run-artifacts` and
`runtime_run_id`) can also be used without changing the selection file.


### Release acceptance reminder

- The first successful Node-API smoke (`NODE_ADDON_PASS`) was on a physical
  **armeabi-v7a** device using the **reference binary**, not a custom build.
- Repeat the version, basic JS, and N-API checks with the self-built runtime.
- A binary compiled for arm64 is not automatically proven by tests on armv7a;
  obtain an actual arm64 on-device result before claiming both ABIs tested.
