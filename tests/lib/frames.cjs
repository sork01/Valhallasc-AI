'use strict';
// Decode a Playwright websocket frame payload. Snapshots arrive as raw-deflate
// binary frames when the client offers compress:true; everything else is text.
const zlib = require('zlib');
function frameText(payload) {
  if (typeof payload === 'string') return payload;
  try { return zlib.inflateRawSync(payload).toString('utf8'); } catch (_) { return payload.toString('utf8'); }
}
function frameJson(payload) { return JSON.parse(frameText(payload)); }
module.exports = { frameText, frameJson };
