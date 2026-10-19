'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');

const addonPath = process.env.NAPI_ADDON_PATH;
assert.ok(addonPath && addonPath.endsWith('.node'));
assert.ok(fs.existsSync(addonPath), 'N-API .node symlink must exist');
console.log('addon.file=' + addonPath);
console.log('node=' + process.version + ' napi=' + process.versions.napi);

let addon;
try {
  addon = require(addonPath);
} catch (err) {
  console.error('NODE_ADDON_LOAD_FAILED: ' + (err && err.stack || err));
  console.error('Hint: standalone Android PIE may not export N-API symbols to dlopen.');
  process.exit(2);
}

assert.equal(addon.apiVersion, 8);
assert.equal(addon.add(19, 23), 42);
assert.equal(addon.add(-7, 7), 0);
console.log('NAPI_MODULE_INIT=PASS');
console.log('NAPI_FUNCTION_CALL=PASS');
console.log('NODE_ADDON_PASS');
