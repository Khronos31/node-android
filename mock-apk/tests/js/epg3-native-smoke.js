'use strict';
// EPGStation 3 beta2 actual production *legacy V8 ABI* native addon loader.
// Use process.dlopen() to isolate C++ module symbol resolution from npm JS
// wrapper dependencies. This is NOT a database-functional test yet.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

console.log('node=' + process.version + ' platform=' + process.platform +
  ' arch=' + process.arch + ' modules=' + process.versions.modules);
function openAddon(variable, label) {
  const file = process.env[variable];
  assert.ok(file && path.isAbsolute(file), label + ': missing native library path');
  assert.ok(fs.existsSync(file), label + ': native library absent');
  console.log(label + '.file=' + file);
  const module = {exports: {}};
  try {
    process.dlopen(module, file);
  } catch (error) {
    console.error('EPG3_NATIVE_LOAD_FAILED module=' + label +
      ' code=' + (error?.code || '(none)') + ' message=' + (error?.message || error));
    console.error(error?.stack || error);
    process.exit(2);
  }
  const keys = Object.keys(module.exports);
  console.log(label + '.exports=' + keys.join(','));
  assert.ok(keys.length > 0, label + ': no exports after dlopen');
  return module.exports;
}

const sqlite = openAddon('EPG3_SQLITE_NATIVE', 'better-sqlite3');
assert.equal(typeof sqlite.Database, 'function', 'missing native Database constructor');
assert.equal(typeof sqlite.setErrorConstructor, 'function', 'missing SQLite error registration');
console.log('BETTER_SQLITE3_NATIVE_LOAD_PASS');
const fsext = openAddon('EPG3_FSEXT_NATIVE', 'fs-ext');
assert.equal(typeof fsext.flock, 'function', 'missing fs-ext flock');
console.log('FS_EXT_NATIVE_LOAD_PASS');
console.log('EPG3_LEGACY_ADDON_PASS');
