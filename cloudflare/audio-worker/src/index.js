// Game Dev Beats — audio Worker
// Serves the embedded audio asset only when called from an allowed Referer.
// Anyone hitting the URL directly (curl, scraper, hot-link from another site)
// gets a 403. Browsers loading the game from playinstigator.com get the file.

import { AUDIO_B64 } from './audio.b64.js';

const ALLOWED_ORIGINS = [
  'https://playinstigator.com',
  'http://localhost:8765',  // local dev
  'http://127.0.0.1:8765',
];

// 1 hour at edge + 1 day in browser. Append ?v=2 to bust caches when audio changes.
const CACHE_CONTROL = 'public, max-age=86400, s-maxage=3600, stale-while-revalidate=86400';

// Decode the base64 once at module load (cold-start cost only).
const AUDIO_BYTES = (() => {
  const bin = atob(AUDIO_B64);
  const buf = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
  return buf;
})();

export default {
  async fetch(request) {
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      return new Response('method not allowed', { status: 405 });
    }

    const referer = request.headers.get('Referer') || '';
    const origin  = request.headers.get('Origin')  || '';
    const allowedOrigin = ALLOWED_ORIGINS.find(o =>
      referer.startsWith(o) || origin === o
    );
    if (!allowedOrigin) {
      return new Response('forbidden', {
        status: 403,
        headers: { 'Cache-Control': 'no-store' },
      });
    }

    const headers = new Headers({
      'Content-Type': 'audio/mpeg',
      'Content-Length': String(AUDIO_BYTES.byteLength),
      'Cache-Control': CACHE_CONTROL,
      'Access-Control-Allow-Origin': allowedOrigin,
      'Vary': 'Origin',
    });

    return new Response(request.method === 'HEAD' ? null : AUDIO_BYTES, { headers });
  },
};
