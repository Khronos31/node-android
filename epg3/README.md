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
- `diskusage-ng@1.0.4` is **pure JavaScript**. It invokes OS-provided
  commands such as `df`; it needs an Android command/output compatibility
  check rather than a native addon cross-build. The absence of `binding.gyp`
  is expected.
- EPGStation 3.0.0-beta2 actually pins **`aribts@2.1.12`** (from
  `rndomhack/node-aribts`), which contains a JavaScript CRC32 implementation
  (`lib/crc32.js`) and depends on `crc@^3.4.4`. It does **not**
  depend on `@node-rs/crc32`. That Rust addon was relevant to the earlier
  EPGStation 2 payload, **not** this EPGStation 3 snapshot. Even though
  `aribts` declares `nan` as a dependency, the upstream package has no
  `binding.gyp` or native `.node` module; TS parsing is still untested on
  Android.

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

## Dedicated real-device legacy V8 loading APK

After both dependency cross-build jobs complete successfully, the same workflow
packages their actual `better_sqlite3.node` and `fs_ext.node` binaries as
`libepg3_better_sqlite3.so` and `libepg3_fs_ext.so` in an isolated Android
mock APK. The **Node runtime is the previously verified own-build run
39220534794**, *not* a third-party reference executable.

The mock APK displays a new fourth button, **EPG3 native ABI**, which invokes
`process.dlopen` directly on the two Android libraries. This deliberately
tests the **real Node/V8 C++ symbol and addon registration compatibility**
before introducing their JavaScript package wrappers.

Expected successes are `BETTER_SQLITE3_NATIVE_LOAD_PASS`,
`FS_EXT_NATIVE_LOAD_PASS` and `EPG3_LEGACY_ADDON_PASS`.
A linker failure is printed as `EPG3_NATIVE_LOAD_FAILED`, with details of
the missing symbol. **A successful load is not yet a SQLite query or a full
EPGStation 3 execution test.**

The existing standalone Node/N-API mock remains separately buildable without
these optional native libraries. Test APKs are debug-signed and must not be
published as production releases.

Android APK staging also includes the matching Android NDK r27
`libc++_shared.so` for both ABIs; Node C++ addons may depend on it at
runtime. The APK verifier checks the payload bytes, not merely their names.

## Production-wrapper SQLite/locking functional test

A fifth mock APK button, **EPG3 functional (SQLite/WAL/flock)**, now extracts
the exact `better-sqlite3@12.11.1` and `fs-ext@2.1.1` production JS
wrappers from the ABI-independent npm package artifacts. The JNI addons remain
extracted in `nativeLibraryDir`; the app creates `.node` symlinks into the
JS package tree and starts the standalone Node executable with
`--preserve-symlinks`.

The new test covers creating a file-backed SQLite database, switching to WAL,
inserting/selecting rows, closing/reopening and reading persisted data, plus
`fs-ext` exclusive nonblocking locks on two separately opened file descriptors.
A returned `EPG3_FUNCTIONAL_PASS` demonstrates functional SQLite/locking, not
merely `process.dlopen`. A failed stage is printed with its own
`EPG3_FUNCTIONAL_FAILED` marker and stack trace.

The test deliberately does not load EPGStation itself or migrate production
SQLite files, and uses only app-private test data.

## Real-device acceptance (2026-10-19)

**Both Android ABIs passed all five stand-alone runtime and dependency tests**
using our independently built Node 24.21.0 and EPGStation 3 beta2 package
versions:

| Test | armeabi-v7a | arm64-v8a |
| --- | --- | --- |
| Node v24 startup | PASS | PASS |
| fs, crypto, child_process, HTTP loopback | PASS | PASS |
| N-API native addon | PASS | PASS |
| Native V8 addon load: better-sqlite3, fs-ext | PASS | PASS |
| Real package JS API: SQLite SQL/WAL/reopen and flock | **PASS** | **PASS** |

The fifth test printed
`EPG3_SQLITE_SQL_PASS`,
`EPG3_SQLITE_WAL_REOPEN_PASS`,
`EPG3_FSEXT_FLOCK_PASS`, and
`EPG3_FUNCTIONAL_PASS` for **both** architectures.

Successful APK build: [GitHub Actions 39247276126](https://github.com/Khronos31/node-android/actions/runs/39247276126).
The on-device observations are documented in [PR #4](https://github.com/Khronos31/node-android/pull/4).

**Unverified:** `diskusage-ng` process execution / `df` output format on
Android, `aribts` TS processing, TypeORM's ESM integration, the actual
EPGStation 3 server process and mirakc connectivity, and database migrations.
No production `dtv-android` APK has been changed.

## EPGStation beta2 JavaScript dependency smoke

A sixth test button exercises the **actual production**
`aribts@2.1.12` and `diskusage-ng@1.0.4` JavaScript packages plus their
runtime dependencies. The probe includes the relevant npm package directory
contents inside APK assets and rejects unanticipated host native libraries.

- `aribts` is required and its MPEG-2 CRC32 implementation is checked
  against the standard vector `123456789` => `0x0376e6e7`.
- `diskusage-ng` uses `child_process.execFile('df', ['-P', '-k', path])`
  on POSIX; the Android app-private directory is queried on the **actual
  device**. This establishes whether the Android `df` command, `PATH`,
  and parser agree. If not, failures are reported rather than falsely marked
  as passing.

Successful `EPG3_JS_DEPS_PASS` is another dependency milestone, but **not**
a claim that EPGStation 3 itself boots or connects to mirakc.

## Android 16 KiB-page ELF safety

Node + EPGStation dependency smoke tests on 4 KiB Android devices do **not**
establish that the binaries load on 16 KiB-page Android. The old mock APK
had `PT_LOAD p_align=0x1000` for `better-sqlite3` and `fs-ext`.
These NDK r27 node-gyp builds now explicitly pass
`-Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384`
to the **target linker**; `epg3/check_pages.py` rejects any 4 KiB
`PT_LOAD` or 16 KiB offset/address incongruence before packaging.
The NDK r27 `libc++_shared.so` used in the original APK was independently
measured to already have 16 KiB PT_LOAD alignment, and is still checked.
The standalone Node PIE and N-API addon changes are tracked separately in
PR #8. A fresh integrated APK must use the corrected Node binary before
claiming that **all** native libraries are 16 KiB-aligned.

This is ELF layout verification, not yet a real 16 KiB-page device test.

## Full 16 KiB-aligned mock APK acceptance

The 16 KiB test APK uses **new own-source-built Node 24.21.0 CI artifacts**
from [run 39308014802](https://github.com/Khronos31/node-android/actions/runs/39308014802),
**not** the prior 4 KiB Node build 39220534794. The mock's N-API smoke
addon uses the linker flags from PR #8, and EPGStation beta2 native
dependencies use the 16 KiB alignment flags from PR #4.

The APK CI inspects **all** native ELF files in `lib/arm64-v8a/*.so`, including
the actual Node executable, N-API addon, better-sqlite3, fs-ext and
`libc++_shared.so`, rejecting any PT_LOAD alignment below 16 KiB.
For 32-bit `armeabi-v7a`, the NDK r27 supplied `libc++_shared.so` is
the only exception (4 KiB), and all custom armv7 native ELFs are still checked.

Passing static inspection does **not** establish correct runtime on a genuine
16 KiB page device. The user should first verify the Android 16 KiB warning
disappears, then repeat tests 1–6, and inspect `adb shell getconf PAGE_SIZE`.
