'use strict';
// Test the exact production JS wrappers + Android-compiled C++ bindings of
// EPGStation 3.0.0-beta2, not just process.dlopen() registration.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = process.env.EPG3_MODULES_ROOT;
const dataDir = process.env.EPG3_DATA_DIR;
assert.ok(root && path.isAbsolute(root));
assert.ok(dataDir && path.isAbsolute(dataDir));
console.log('node=' + process.version + ' arch=' + process.arch +
  ' modules=' + process.versions.modules);

let stage = 'load';
try {
  // Actual better-sqlite3 v12.11.1 lib/index.js, lib/database.js, and
  // methods/*.js. Its nativeBinding option resolves our .node symlink.
  const Database = require(path.join(root, 'better-sqlite3/lib/index.js'));
  const nativeBinding = path.join(root, 'better-sqlite3/better_sqlite3.node');
  assert.ok(fs.existsSync(nativeBinding));
  const dbPath = path.join(dataDir, 'epg3-functional-' + process.arch + '.db');
  stage = 'sqlite-open';
  let db = new Database(dbPath, {nativeBinding});
  try {
    stage = 'sqlite-sql';
    db.exec('DROP TABLE IF EXISTS smoke; CREATE TABLE smoke (id INTEGER PRIMARY KEY, value TEXT NOT NULL)');
    const journal = db.pragma('journal_mode = WAL', {simple: true});
    assert.equal(String(journal).toLowerCase(), 'wal');
    db.prepare('INSERT INTO smoke (value) VALUES (?)').run('EPG3 Android');
    const row = db.prepare('SELECT value FROM smoke WHERE id = ?').get(1);
    assert.equal(row.value, 'EPG3 Android');
    console.log('EPG3_SQLITE_SQL_PASS');

    stage = 'sqlite-reopen';
  } finally {
    db.close();
  }
  db = new Database(dbPath, {nativeBinding});
  try {
    const row = db.prepare('SELECT value FROM smoke WHERE id = ?').get(1);
    assert.equal(row.value, 'EPG3 Android');
    assert.equal(String(db.pragma('journal_mode', {simple: true})).toLowerCase(), 'wal');
    console.log('EPG3_SQLITE_WAL_REOPEN_PASS');
  } finally {
    db.close();
  }

  stage = 'fs-ext-lock';
  // Exact fs-ext fs-ext.js wrapper calls the real fs_ext.node binding.
  const fsExt = require(path.join(root, 'fs-ext/fs-ext.js'));
  const file = path.join(dataDir, 'epg3-flock-' + process.arch + '.lock');
  const fd1 = fs.openSync(file, 'w+');
  const fd2 = fs.openSync(file, 'r+');
  try {
    fsExt.flockSync(fd1, 'exnb');
    assert.throws(() => fsExt.flockSync(fd2, 'exnb'),
      error => error?.code === 'EWOULDBLOCK' || error?.code === 'EAGAIN');
    fsExt.flockSync(fd1, 'un');
    fsExt.flockSync(fd2, 'exnb');
    fsExt.flockSync(fd2, 'un');
    console.log('EPG3_FSEXT_FLOCK_PASS');
  } finally {
    fs.closeSync(fd2);
    fs.closeSync(fd1);
  }
  console.log('EPG3_FUNCTIONAL_PASS');
} catch (error) {
  console.error('EPG3_FUNCTIONAL_FAILED stage=' + stage + ' code=' +
    (error?.code || '(none)'));
  console.error(error?.stack || error);
  process.exitCode = 2;
}
