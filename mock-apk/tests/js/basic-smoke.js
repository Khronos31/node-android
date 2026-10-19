'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const http = require('node:http');
const childProcess = require('node:child_process');

assert.match(process.version, /^v24\./);
assert.equal(process.platform, 'android');
assert.ok(process.arch === 'arm' || process.arch === 'arm64');
console.log('node=' + process.version + ' platform=' + process.platform + ' arch=' + process.arch);

const tmp = process.env.TMPDIR;
assert.ok(tmp, 'TMPDIR must be set to app cache dir');
const filename = path.join(tmp, 'mock-fs-test.txt');
try {
  fs.writeFileSync(filename, 'node-android', 'utf8');
  assert.equal(fs.readFileSync(filename, 'utf8'), 'node-android');
  console.log('filesystem=PASS');
} finally {
  try { fs.unlinkSync(filename); } catch (_) { /* test file may not exist */ }
}

assert.equal(
  crypto.createHash('sha256').update('abc').digest('hex'),
  'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
);
console.log('crypto=PASS');

const spawned = childProcess.spawnSync(process.execPath, [
  '-e', 'process.stdout.write("spawn-ok")'
], { encoding: 'utf8', timeout: 5000 });
assert.equal(spawned.status, 0, spawned.stderr || String(spawned.error));
assert.equal(spawned.stdout, 'spawn-ok');
console.log('child_process=PASS');

const server = http.createServer((_req, response) => {
  response.writeHead(200, { 'content-type': 'text/plain' });
  response.end('pong');
});
server.on('error', error => { console.error(error); process.exitCode = 1; });
server.listen(0, '127.0.0.1', () => {
  const request = http.get({
    hostname: '127.0.0.1',
    port: server.address().port,
    path: '/health',
    timeout: 5000
  }, response => {
    let body = '';
    response.setEncoding('utf8');
    response.on('data', chunk => { body += chunk; });
    response.on('end', () => {
      if (response.statusCode !== 200 || body !== 'pong') {
        console.error('http=FAIL status=' + response.statusCode + ' body=' + body);
        process.exitCode = 1;
      } else {
        console.log('http.loopback=PASS');
        console.log('NODE_BASIC_PASS');
      }
      server.close();
    });
  });
  request.on('timeout', () => request.destroy(new Error('timeout')));
  request.on('error', error => {
    console.error(error);
    process.exitCode = 1;
    server.close();
  });
});
