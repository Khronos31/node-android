'use strict';
// Real EPGStation 3.0.0-beta2 production JS package smoke on Android.
// No tuner required; no edits to production config or database.
const assert = require('node:assert/strict');
const path = require('node:path');
const root = process.env.EPG3_MODULES_ROOT;
const dataDir = process.env.EPG3_DATA_DIR;
assert.ok(root && path.isAbsolute(root), 'Missing EPG3_MODULES_ROOT');
assert.ok(dataDir && path.isAbsolute(dataDir), 'Missing EPG3_DATA_DIR');
console.log('node=' + process.version + ' arch=' + process.arch);
console.log('PATH=' + process.env.PATH);

(async () => {
  let stage = 'aribts';
  try {
    const aribts = require(path.join(root, 'node_modules/aribts'));
    assert.equal(typeof aribts.TsCrc32?.calc, 'function');
    assert.equal(typeof aribts.TsPacketParser, 'function');
    assert.equal(aribts.TsCrc32.calc(Buffer.from('123456789')) >>> 0,
      0x0376e6e7, 'MPEG-2 CRC32 known vector');
    console.log('EPG3_ARIBTS_CRC_PASS');

    stage = 'diskusage';
    const diskusage = require(path.join(root, 'node_modules/diskusage-ng'));
    assert.equal(typeof diskusage, 'function');
    const usage = await new Promise((resolve, reject) => {
      diskusage(dataDir, (error, result) => error ? reject(error) : resolve(result));
    });
    assert.ok(Number.isFinite(usage.total) && usage.total > 0);
    assert.ok(Number.isFinite(usage.available) && usage.available >= 0);
    assert.ok(usage.available <= usage.total);
    console.log('diskusage.total=' + usage.total + ' available=' + usage.available);
    console.log('EPG3_DISKUSAGE_DF_PASS');
    console.log('EPG3_JS_DEPS_PASS');
  } catch (error) {
    console.error('EPG3_JS_DEPS_FAILED stage=' + stage +
      ' code=' + (error?.code || '(none)'));
    console.error(error?.stack || error);
    process.exitCode = 2;
  }
})();
