'use strict';
// Run on the device with: <nativeLibraryDir>/libnode_exec.so smoke.js
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');

assert.equal(process.platform, 'android');
assert(Number(process.versions.node.split('.')[0]) >= 24);
console.log('node=' + process.version + ' arch=' + process.arch);

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'node-android-'));
try {
  const target = path.join(dir, 'smoke.txt');
  fs.writeFileSync(target, 'node-android');
  assert.equal(fs.readFileSync(target, 'utf8'), 'node-android');
  console.log('filesystem=PASS');
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
assert.equal(
  crypto.createHash('sha256').update('abc').digest('hex'),
  'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
);
console.log('crypto=PASS');
const server = http.createServer((_req, res) => res.end('pong'));
server.listen(0, '127.0.0.1', () => {
  const req = http.get({host:'127.0.0.1',port:server.address().port,timeout:5000}, res => {
    let body = '';
    res.on('data', chunk => body += chunk);
    res.on('end', () => {
      try {
        assert.equal(body, 'pong');
        console.log('http.loopback=PASS');
        console.log('NODE_SMOKE_PASS');
      } catch (error) {
        console.error(error);
        process.exitCode = 1;
      } finally {
        server.close();
      }
    });
  });
  req.on('error', error => {
    console.error(error);
    process.exitCode = 1;
    server.close();
  });
  req.on('timeout', () => req.destroy(new Error('timeout')));
});
