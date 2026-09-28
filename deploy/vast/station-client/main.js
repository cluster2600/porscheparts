import { AppStreamer, EventStatus, StreamType } from './vendor/ov-web-rtc.js';
import { directConfig } from './config.mjs';

const stream = new AppStreamer();
const byId = id => document.getElementById(id);
const video = byId('remote-video');
const evidence = { client: '@nvidia/ov-web-rtc@6.7.0', events: [], frames: 0, connections: 0 };
let active = false;
function status(message) { byId('status').textContent = message; }
function event(message) {
  evidence.events.push({ at: new Date().toISOString(), action: message.action, status: message.status });
  evidence.events = evidence.events.slice(-200);
  if (message.status === EventStatus.ERROR) status('Échec de diffusion. Vérifier le tunnel SSH et le port UDP externe.');
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
    controls(true);
    status('Connexion à la station…');
    const result = await stream.connect({ streamSource: StreamType.DIRECT, streamConfig: {
      ...config, onStart: event, onUpdate: event, onStop: event,
      onTerminate: event,
      onStreamStats: stats => { evidence.streamStats = stats; },
    } });
    event(result);
    if (result.status === EventStatus.ERROR || result.status === EventStatus.CANCELED) throw new Error('La connexion a échoué.');
    evidence.connections += 1;
    status('Signalisation établie ; attente de la première image décodée…');
  } catch (error) {
    await stream.terminate().catch(() => {});
    active = false;
    controls(false);
    status(error.message || 'Connexion impossible.');
  }
});
byId('disconnect').addEventListener('click', async () => {
  controls(false);
  byId('connect').disabled = true;
  try { await stream.terminate(); }
  finally { active = false; controls(false); status('Déconnecté. La scène reste ouverte sur la station.'); }
});
video.addEventListener('playing', () => status('Image reçue. L’éditeur est disponible.'));
function frame(_now, metadata) {
  evidence.frames += 1;
  evidence.video = { width: video.videoWidth, height: video.videoHeight, mediaTime: metadata.mediaTime, presentedFrames: metadata.presentedFrames };
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
