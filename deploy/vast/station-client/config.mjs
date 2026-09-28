export function directConfig(mediaServer, mediaPort) {
  const octets = mediaServer.trim().split('.');
  if (octets.length !== 4 || octets.some(value => !/^\d{1,3}$/.test(value) || Number(value) > 255)) {
    throw new Error('Enter the public IPv4 address supplied by Vast.');
  }
  if (!/^\d+$/.test(String(mediaPort)) || Number(mediaPort) < 1 || Number(mediaPort) > 65535) {
    throw new Error('Enter the external UDP port mapped to 47998 by Vast.');
  }
  return {
    signalingServer: '127.0.0.1', signalingPort: 49100, signalingPath: '/',
    mediaServer: mediaServer.trim(), mediaPort: Number(mediaPort),
    width: 1920, height: 1080, fps: 30, fitStreamResolution: false,
    videoElementId: 'remote-video', audioElementId: 'remote-audio',
    enableAV1Support: false, mic: false, maxReconnects: 3,
  };
}
