'use strict';
// Host-side regression for Android's .node -> lib*.so symlink convention.
// No native addon is loaded here; we verify CommonJS filename resolution.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'napi-link-'));
try {
  const target = path.join(dir, 'libnapi_smoke.so');
  const link = path.join(dir, 'napi-smoke.node');
  fs.writeFileSync(target, 'ELF placeholder; do not require()', 'utf8');
  fs.symlinkSync(target, link);
  const resolved = require.resolve(link);
  const preserve = process.execArgv.includes('--preserve-symlinks');
  assert.equal(resolved, preserve ? link : target);
  console.log('COMMONJS_SYMLINK_RESOLVE_PASS preserve=' + preserve +
              ' extension=' + path.extname(resolved));
} finally {
  fs.rmSync(dir, {recursive: true, force: true});
}
