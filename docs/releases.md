# Binary release process

Node Android publishes standalone Node **PIE executables**, not an Android
JNI `libnode.so`, and **not** `nodejs-mobile`. The initial port revision
uses Git tag `v24.21.0-android.1` (a GitHub **pre-release**).

## Download and verification

Permanent assets in [GitHub Releases](https://github.com/Khronos31/node-android/releases):

- `node-v24.21.0-android-armeabi-v7a.tar.xz`
- `node-v24.21.0-android-arm64-v8a.tar.xz`
- `SHA256SUMS` for both archives
- `RELEASE-METADATA.json` recording source, CI run and patch fingerprints

For example:

```sh
sha256sum -c SHA256SUMS
tar -tJf node-v24.21.0-android-arm64-v8a.tar.xz
```

Each archive contains `bin/node` (the executable), the official Node
`LICENSE` including third-party notices, `BUILD-METADATA.json` and
an internal `SHA256SUMS`.

The Android executable is renamed to `libnode_exec.so` when staged into an
APK's `jniLibs/<abi>/`, allowing extraction to
`ApplicationInfo.nativeLibraryDir`. Use `ProcessBuilder` to execute it.
Do **not** interpret it as a shared `libnode.so` or copy it to a writable
directory and attempt to execute it on modern Android. npm is not bundled.

## Controlled publication

[Release promotion](../.github/workflows/release.yml) is a **manually
dispatched** and tag-gated action run from `main` after the tag exists. It reuses reviewed successful two-ABI CI
archives **without recompiling**. It refuses to publish when:

- The dispatch is not on the repository's `main` branch, the named tag
  does not exist, or the tag commit is not an ancestor of `main`.
- The tagged build inputs and patch scripts differ from the promotion
  workflow checkout. (The release verification tool itself can be fixed
  without moving an already-created, unpublished tag.)
- The CI run was not successful or is not this repository's Node build.
- The build source HEAD is not an ancestor of the release tag.
- Either ABI archive is missing or extra archives appear.
- Any internal sha256, ELF architecture/class/PIE type, official source SHA,
  Android patch hash or NDK pin disagrees with the tagged repository.
- The tag has an existing GitHub Release.

The resulting `RELEASE-METADATA.json` distinguishes the build run's source
checkout, the **immutable release tag commit** and the **promotion workflow
checkout**. It never claims that the binary was recompiled from the tag
or that a verification-tool fix changed the release's source inputs.

**Initial candidate:** source build workflow run `39240791051`,
feature source head `86d74118b9e8d851a00fe96ad8bb74ed90903e9c`
(merged via PR #1). The original source/patch-matched workflow
`39220534794` underwent real-Android testing with both ABIs, including
native and JS EPGStation 3 dependency smoke tests. The particular promoted
`-j4` binaries were not independently retested byte-for-byte, hence
the **pre-release** designation.

No full EPGStation runtime, storage migrations, or tuner compatibility is
promised by this release. Downstream consumers should **pin the released
archive SHA-256** and keep license notices.
