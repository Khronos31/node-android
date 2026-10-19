# Node.js Android CI build cache

The initial full V8 build can take hours. **This optimization applies only to
future runs**: it cannot retrofit caching into an already-running GitHub job.

## What we cache

| Component | Cache location | Key isolation | Policy |
| --- | --- | --- | --- |
| ccache compiler results | `.ccache/<ABI>/` | OS, runner architecture, Android ABI, pinned source+patch+script fingerprint | Max 1500 MB **per ABI**, compressed |
| Pinned V8 host LLVM | `.work/<ABI>/llvm-host/` | OS, runner architecture, ABI, Node source lock | Used only if matching LLVM binary is already present |

The **Android NDK is not cached** (it is very large), and neither are V8's
full Ninja intermediate directories. Caching those directly risks consuming
GitHub Actions' repository cache quota and costs substantial restore/upload
time. The official Node source archive is checksum-verified and quick to
download, so it is not cached either.

Node's official [BUILDING.md](https://github.com/nodejs/node/blob/v24.21.0/BUILDING.md)
explicitly recommends `CC="ccache gcc"` and `CXX="ccache g++"` for frequent
rebuilds. Here we wrap **Android NDK Clang and the pinned V8 host LLVM Clang**,
while retaining the original link commands. `ccache` verifies the actual
compiler contents and inputs; it is not an uncontrolled reuse of binaries.

## Build parallelism

With the public-repository Ubuntu x64 GitHub-hosted runner's **4 vCPUs / 16 GB
RAM**, CI now uses `NODE_ANDROID_JOBS=4` (`ninja -j4`). Each Android ABI
gets a separate runner and its own memory allocation; the two concurrent
matrix jobs do not share one 16 GB limit.

This is a **proposed default**, not yet benchmarked. V8 C++ compilation can
occasionally peak in memory usage; if the job exits with SIGKILL/137/OOM,
reduce the job count to 3 and compare performance. Each run logs CPU/memory
and filesystem capacity immediately before compilation.

Local builds can override `NODE_ANDROID_JOBS` to fit their hardware.

## Cache lifetime / failures

- `actions/cache/restore@v4` runs **before** compilation.
- Every workflow run attempt uses a **unique primary cache key**, because
  GitHub Actions cache entries are immutable once saved.
- Restore-keys reuse the most recent cache for the exact Node source,
  patch/script set, ABI, and runner platform.
- `actions/cache/save@v4` is allowed after a failed compilation so the next
  run can reuse successfully compiled translation units, provided the cache
  directory contains data. It does **not** publish a Node.js binary.
- `CCACHE_MAXSIZE=1500M` bounds the stored compiler cache for each ABI.
  GitHub cache retention and eviction policies still apply.
- The very first cache-enabled build will generally show misses; only
  subsequent runs can report meaningful hits.
- PR-created caches can have visibility limitations across different PR merge
  refs, so hitting the cache on unrelated branches is not guaranteed.

## How to check whether it worked

Inspect the Actions job logs at the `Report cache statistics and presence`
step. Look for `Cache hit`/`Cache miss`, `cache hit (direct)`,
`cache hit (preprocessed)`, and `cache miss`. Use **actual CI logs** to
evaluate speedups; no acceleration percentage is promised.

## Validation strategy

This cache PR is intentionally stacked on the Node build PR. The heavyweight
`build` job is **skipped only when this PR targets**
`feat/node24-android-build`, so opening the cache PR does not launch a second
multi-hour V8 compile. The existing source/patch validation still runs. Once
merged into the underlying feature branch, normal PR builds against `main`
will exercise the caching changes.

To run without ccache on a local host, simply omit
`NODE_ANDROID_USE_CCACHE=1`. This keeps local builds unchanged.
