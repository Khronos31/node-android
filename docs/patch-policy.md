# Patch policy

This is **not** a fork of Node.js. Each build downloads a SHA-256-verified
official source archive, then applies the pinned Android-specific patch set.

- The first patch set is a **candidate compatibility baseline**, not a claim
  that every patch remains necessary in Node v24.21.0. Remove patches after
  confirming an upstream fix or a successfully tested build without them.
- Apply only patches in `patches/node-24/` in lexical order. A patch that is
  already applied is accepted (reentrant build); an incompatible patch is fatal.
  We never silently discard .rej files or use fallbacks that hide patch failures.
- Keep one patch per purpose. Record provenance and the reason for carrying it.
- Do not import Termux-specific prefixes, paths, npm packages, or shared-library
  dependencies. Bundle Node's OpenSSL, ICU, zlib and libuv by default.
- Do not remove Android/ARM branch protection merely to support obsolete NDKs.
- Prefer submitting general-purpose fixes upstream; drop patches once accepted.
- New Node versions require explicit source SHA verification, clean-tree patch
  application, separate armv7a/arm64 builds, ELF inspection, and device tests.

## Provenance & license

Initial compatibility patches and `cpu-features.h` were copied from
[Delusions6515/node-android-build](https://github.com/Delusions6515/node-android-build/tree/8255800ed90e1c4a1ab5c9d33bf8f1fd46976504)
(commit `8255800ed90e1c4a1ab5c9d33bf8f1fd46976504`, `patches/24`).
The files labeled `termux` there originate from
[Termux's Node package patches](https://github.com/termux/termux-packages/tree/master/packages/nodejs-lts).
Termux's [LICENSE.md](https://github.com/termux/termux-packages/blob/master/LICENSE.md)
specifies that package patches are licensed like the corresponding package;
the Node.js package is MIT. The upstream Node.js LICENSE and any third-party
dependency notices must accompany binary distributions. The initial helper
repository is also MIT-licensed. See `LICENSE` for this repository's own code.

Port-specific patches should remain upstream-compatible, and any exception to
licensing assumptions must be reviewed before publishing build artifacts.
