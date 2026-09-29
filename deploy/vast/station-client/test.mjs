import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
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

test('asynchronous start needs SUCCESS and a decoded frame; exhausted retries unlock connect', async () => {
  const nodes = new Map();
  for (const id of ['remote-video', 'status', 'connect', 'disconnect', 'connection', 'media-host', 'media-port', 'evidence']) {
    nodes.set(id, { disabled: false, handlers: {}, addEventListener(type, callback) { this.handlers[type] = callback; } });
  }
  nodes.get('media-host').value = '127.0.0.1';
  nodes.get('media-port').value = '47998';
  const video = nodes.get('remote-video');
  video.requestVideoFrameCallback = callback => { video.frameCallback = callback; };
  video.videoWidth = 1920;
  video.videoHeight = 1080;
  let callbacks;
  class AppStreamer {
    async connect(props) {
      callbacks = props.streamConfig;
      callbacks.onStreamStatusChange(0);
      callbacks.onStreamStatusChange(1);
      return { status: 'inProgress' };
    }
    async terminate() {}
  }
  const context = vm.createContext({
    AppStreamer, directConfig, Date, setTimeout,
    EventStatus: { SUCCESS: 'success', ERROR: 'error', CANCELED: 'canceled', WARNING: 'warning' },
    StreamStatus: { NONE: 0, STARTING: 1, STREAMING: 2, STOPPED: 4 },
    StreamType: { DIRECT: 'direct' },
    document: { getElementById: id => nodes.get(id) },
    window: { addEventListener() {} },
  });
  const source = readFileSync(new URL('./main.js', import.meta.url), 'utf8').replace(/^import .*;\n/gm, '');
  vm.runInContext(source, context);
  await nodes.get('connection').handlers.submit({ preventDefault() {} });
  assert.equal(vm.runInContext('evidence.connections', context), 0);
  assert.equal(nodes.get('connect').disabled, true);
  callbacks.onStart({ status: 'success' });
  assert.equal(vm.runInContext('evidence.connections', context), 1);
  assert.match(nodes.get('status').textContent, /attente/);
  video.frameCallback(100, { mediaTime: 1, presentedFrames: 1 });
  assert.match(nodes.get('status').textContent, /éditeur est disponible/);
  callbacks.onStart({ status: 'success' });
  assert.equal(vm.runInContext('evidence.connections', context), 1);
  callbacks.onUpdate({ status: 'error' });
  callbacks.onStreamStatusChange(4);
  assert.equal(nodes.get('connect').disabled, false);
  assert.equal(nodes.get('disconnect').disabled, true);
  assert.match(nodes.get('status').textContent, /Échec/);
  await nodes.get('connection').handlers.submit({ preventDefault() {} });
  callbacks.onStart({ status: 'success' });
  callbacks.onStart({ status: 'error' });
  video.frameCallback(200, { mediaTime: 2, presentedFrames: 2 });
  assert.match(nodes.get('status').textContent, /Échec/);
  assert.equal(nodes.get('connect').disabled, false);
});
