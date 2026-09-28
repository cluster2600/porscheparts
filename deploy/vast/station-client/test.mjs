import assert from 'node:assert/strict';
import { test } from 'node:test';
import { directConfig } from './config.mjs';

test('private signaling and explicit NAT media mapping', () => {
  const config = directConfig(' 203.0.113.10 ', '32147');
  assert.equal(config.signalingServer, '127.0.0.1');
  assert.equal(config.signalingPort, 49100);
  assert.equal(config.mediaServer, '203.0.113.10');
  assert.equal(config.mediaPort, 32147);
  for (const address of ['', 'evil.test/path', '256.0.0.1', '1.2.3', '1.2.3.4:80']) {
    assert.throws(() => directConfig(address, '32147'));
  }
  for (const port of ['', '0', '65536', '12.5', '-1', 'abc']) {
    assert.throws(() => directConfig('203.0.113.10', port));
  }
});
