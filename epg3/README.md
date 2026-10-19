# EPGStation 3 Android: native-dependency compatibility gate

This is a **separate investigation**, not a change to `dtv-android` and
not a claim that EPGStation 3 starts on Android. The next milestone after the
standalone Node v24.21.0 PoC is identifying and compiling **real production
native dependencies**.

## Upstream snapshot

- EPGStation [`3.0.0-beta2`](https://github.com/l3tnun/EPGStation), upstream
  snapshot commit `1793ab74088be8791d191c9621ab881e50741119`
- Requires Node `>=24`; our source-built Node 24.21.0 has already passed
  version, filesystem, crypto, child_process, HTTP loopback and N-API addon
  on physical devices for both `armeabi-v7a` and `arm64-v8a`.
- Default SQLite driver in v3 is **better-sqlite3 12.11.1**, not the
  `sqlite3` addon from dtv-android's v2.10.0 payload.
- `better-sqlite3@12.11.1` uses Node/V8 C++ binding APIs, **not Node-API**
  (its [v12.11.1 binding.gyp](https://github.com/WiseLibs/better-sqlite3/blob/v12.11.1/binding.gyp)
  depends on SQLite and directly compiles `src/better_sqlite3.cpp`).
  **Passing the Node-API smoke alone cannot establish compatibility.**
- `fs-ext@2.1.1` uses NAN/V8 C++ bindings, not Node-API.
- `diskusage-ng@1.0.4` is included in the exact dependency audit. Its
  package build metadata is probed rather than assuming it is pure JS.
- `aribts` and its transitive CRC32 bindings still require an Android-specific
  dependency check, especially `@node-rs/crc32` and nested binary packages.

## What this PR runs

`epg3/build-android-native.sh` pins the above three production modules and
node-gyp; it checks the exact dependency versions against EPGStation's
**pinned Git commit**, then uses the pinned Android NDK r27 toolchain and
Node v24.21.0 official development headers to cross-compile each addon in
two independent GitHub Actions jobs.

Outputs: an ABI-specific set of `.node` ELF binaries and hashes. A passing
build **only proves static cross-compilation**. It does not establish dynamic
linking, module initialisation or SQLite functionality on Android.

## Next gates after this build succeeds

1. Stage ELF addons inside an Android APK's `nativeLibraryDir` as
   `lib*.so` with app-private `.node` symlinks, as in the existing N-API
   mock. A legacy V8 addon must be loaded using the *exact* Node 24 module ABI.
2. Test `better-sqlite3` database creation, a query, WAL mode, and reopen
   with `fs-ext` and `diskusage-ng` APIs from an Android device.
3. Separately evaluate EPGStation 3 startup, TypeORM, ESM, the CRC32 binding,
   configuration migration, and subprocess launch behavior.
4. Only then prepare a `dtv-android` implementation PR. **Do not silently
   replace EPGStation v2 or release an APK** during this probe.

This workflow intentionally does not trigger the multi-hour Node.js runtime
cross-build, and it does not run any HAOS subagents.
