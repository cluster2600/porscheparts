import { AppStreamer, EventStatus, StreamStatus, StreamType } from './vendor/ov-web-rtc.js';
import { directConfig } from './config.mjs';

const stream = new AppStreamer();
const byId = id => document.getElementById(id);
const video = byId('remote-video');
const evidence = { client: '@nvidia/ov-web-rtc@6.7.0', events: [], frames: 0, connections: 0 };
let active = false;
let connected = false;
let framesAtConnect = 0;
function status(message) { byId('status').textContent = message; }
function event(message) {
  evidence.events.push({ at: new Date().toISOString(), action: message.action, status: message.status, info: String(message.info || '') });
  evidence.events = evidence.events.slice(-200);
  if (message.status === EventStatus.ERROR) status('Échec de diffusion. Vérifier le tunnel SSH et le port UDP externe.');
}
function started(message) {
  event(message);
  if (message.status === EventStatus.SUCCESS && !connected) {
    connected = true;
    evidence.connections += 1;
    status(evidence.frames > framesAtConnect ? 'Image reçue. L’éditeur est disponible.' : 'Flux connecté ; attente de la première image décodée…');
  } else if (message.status === EventStatus.WARNING) {
    status('Connexion en cours de nouvelle tentative…');
  } else if (message.status === EventStatus.ERROR || message.status === EventStatus.CANCELED) {
    active = false;
    connected = false;
    controls(false);
  }
}
function controls(busy) {
  byId('connect').disabled = busy;
  byId('disconnect').disabled = !busy;
}
byId('connection').addEventListener('submit', async e => {
  e.preventDefault();
  if (active) return;
  try {
    const config = directConfig(byId('media-host').value, byId('media-port').value);
    active = true;
    connected = false;
    framesAtConnect = evidence.frames;
    controls(true);
    status('Connexion à la station…');
    const result = await stream.connect({ streamSource: StreamType.DIRECT, streamConfig: {
      ...config, onStart: started, onUpdate: event, onStop: event,
      onTerminate: event,
      onStreamStatusChange: state => {
        const previous = evidence.streamStatus;
        evidence.streamStatus = state;
        if (state === StreamStatus.STOPPED || (state === StreamStatus.NONE && previous !== undefined && previous !== StreamStatus.NONE)) {
          active = false;
          connected = false;
          controls(false);
        }
      },
      onStreamStats: message => {
        const stats = message.data?.stats;
        if (stats) evidence.streamStats = Object.fromEntries([
          'codec', 'fps', 'rtd', 'avgDecodeTime', 'frameLoss', 'packetLoss',
          'totalBandwidth', 'currentBitrate', 'utilizedBandwidth',
          'streamingResolutionWidth', 'streamingResolutionHeight',
        ].map(key => [key, stats[key]]));
      },
    } });
    event(result);
    if (result.status === EventStatus.ERROR || result.status === EventStatus.CANCELED) throw new Error('La connexion a échoué.');
  } catch (error) {
    connected = false;
    await stream.terminate().catch(() => {});
    active = false;
    controls(false);
    status(error.message || 'Connexion impossible.');
  }
});
byId('disconnect').addEventListener('click', async () => {
  connected = false;
  controls(false);
  byId('connect').disabled = true;
  try { await stream.terminate(); }
  finally { active = false; controls(false); status('Déconnecté. La scène reste ouverte sur la station.'); }
});
function frame(_now, metadata) {
  evidence.frames += 1;
  evidence.video = { width: video.videoWidth, height: video.videoHeight, mediaTime: metadata.mediaTime, presentedFrames: metadata.presentedFrames };
  if (connected && evidence.frames === framesAtConnect + 1) status('Image reçue. L’éditeur est disponible.');
  video.requestVideoFrameCallback(frame);
}
if (video.requestVideoFrameCallback) video.requestVideoFrameCallback(frame);
byId('evidence').addEventListener('click', () => {
  const url = URL.createObjectURL(new Blob([JSON.stringify(evidence, null, 2)], { type: 'application/json' }));
  const a = document.createElement('a');
  a.href = url; a.download = 'station-webrtc-diagnostic.json'; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
window.addEventListener('pagehide', () => { void stream.terminate(); });
