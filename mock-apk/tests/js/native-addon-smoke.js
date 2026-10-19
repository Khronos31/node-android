'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const addonPath = process.env.NAPI_ADDON_PATH;
assert.ok(addonPath && addonPath.endsWith('.node'));
assert.ok(fs.existsSync(addonPath), 'N-API .node symlink must exist');
console.log('addon.file=' + addonPath);
console.log('node=' + process.version + ' napi=' + process.versions.napi);
console.log('node.execArgv=' + JSON.stringify(process.execArgv));
console.log('addon.realpath=' + fs.realpathSync(addonPath));

let addon;
try {
  // Normally CJS resolves symlinks to their real path, ending in .so.
  // Node then falls back to the JavaScript loader. The Android launcher
  // uses --preserve-symlinks so the resolved name retains its .node suffix.
  const resolved = require.resolve(addonPath);
  console.log('addon.resolved=' + resolved);
  assert.equal(path.extname(resolved), '.node',
    'Node resolved the addon symlink to a non-.node filename; check --preserve-symlinks');
  addon = require(addonPath);
} catch (err) {
  console.error('NODE_ADDON_LOAD_FAILED: ' + (err && err.stack || err));
  if (err?.code === 'ERR_DLOPEN_FAILED') {
    console.error('stage=dlopen; inspect missing N-API symbols or Android linker namespace');
  } else if (err instanceof SyntaxError) {
    console.error('stage=module-loader; ELF was treated as JavaScript');
  } else {
    console.error('stage=resolve-or-module-initialization');
  }
  process.exit(2);
}

assert.equal(addon.apiVersion, 8);
assert.equal(addon.add(19, 23), 42);
assert.equal(addon.add(-7, 7), 0);
console.log('NAPI_MODULE_INIT=PASS');
console.log('NAPI_FUNCTION_CALL=PASS');
console.log('NODE_ADDON_PASS');
