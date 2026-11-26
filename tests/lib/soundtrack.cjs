const manifest = require('node:fs').readFileSync(require('node:path').resolve(__dirname, '../../scripts/soundtrack-filedrop.txt'), 'utf8');
const tracks = new Map(JSON.parse(manifest).tracks.map(track => [track.slot, track]));
module.exports = slot => {
  const track = tracks.get(slot);
  if (!track) throw new Error(`Unknown soundtrack slot ${slot}`);
  return track.loop_seconds ?? track.seconds;
};
