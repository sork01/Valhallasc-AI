#!/bin/sh
# Correct the active Greenmeadow night project at its native 100 BPM, 6/8 grid.
set -eu
if [ -z "${DYB2_CHROME:-}" ] && [ -x /tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell ]; then
  export DYB2_CHROME=/tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell
fi
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const project_id = '6c52c389c99ed898';
const client = new Client({ name: 'valhallasc-meadow-night-rhythm', version: '1' });
await client.connect(new StdioClientTransport({
  command: process.execPath, args: ['--import', 'tsx', 'mcp/server.mjs'],
  cwd: process.cwd(), stderr: 'inherit', env: { ...process.env, DYB2_MCP_USER: 'codex' },
}));
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: { project_id, ...args } }, undefined, { timeout: 300000 });
  if (result.isError) throw Error(`${name}: ${result.content.map(x => x.text).join('\n')}`);
  return JSON.parse(result.content[0].text);
}
function row(hits, accents = []) {
  const steps = Array(24).fill('.'); // two 6/8 bars, 12 sixteenths each
  for (const step of hits) steps[step] = accents.includes(step) ? 'X' : 'x';
  return steps.join('');
}

const project = await call('open_project');
if (project.project_id !== project_id || project.tempo !== '100 bpm' || project.meter !== '6/8' || project.bars !== 32) {
  throw Error('The active Greenmeadow night project has changed; inspect it before editing.');
}
for (const track of ['Kantele', 'Flute', 'Bass', 'Strings', 'Harp', 'Night breakbeat']) {
  if (!project.tracks.some(t => t.name === track)) throw Error(`Missing track: ${track}`);
}

// The harp used dotted-sixteenth placements (.75, 1.5, 2.25 quarter-note
// beats) that cut across both eighth-note groups. Put its three notes on a
// stable 6/8 pulse: the offbeat before each dotted-quarter accent, the second
// accent itself, and the last eighth as a pickup. Keep pitches and dynamics.
const harp = [];
for (let from_bar = 1; from_bar <= 32; from_bar += 8) {
  const view = await call('view_track', { track: 'Harp', from_bar, bars: 8, as: 'notes' });
  for (const note of view.notes) {
    const bar = Math.floor(note.beat / 3);
    const within = +(note.beat - bar * 3).toFixed(3);
    const target = Math.abs(within - .75) < .001 ? .5
      : Math.abs(within - 1.5) < .001 ? 1.5
      : Math.abs(within - 2.25) < .001 ? 2.5
      : [0.5, 1.5, 2.5].includes(within) ? within : null;
    if (target === null) throw Error(`Unexpected harp timing: bar ${from_bar + bar}, beat ${within}`);
    harp.push({ ...note, beat: (from_bar - 1 + bar) * 3 + target });
  }
}
if (harp.length !== 96) throw Error(`Expected 96 harp notes, found ${harp.length}`);
await call('write_notes', { track: 'Harp', start_bar: 1, bars: 32, name: 'Firefly pulses in 6/8', notes: harp });

// The answering flute uses Dexed's WHISTLE FLUTE. Its note positions are
// already on sixteenths. Do not substitute Sork-60 Whistle or another lead.
await call('set_instrument', { track: 'Flute', instrument: 'dexed', preset: 'WHISTLE FLUTE' });

// The old beat missed the second dotted-quarter snare in alternating intro
// bars and swung isolated sixteenths into inconsistent pickups. Keep a
// distinct, restrained Chillhop break, but anchor both bars in every section
// with kicks on beat 0, snares on beat 1.5, and eighth-note hats.
await call('clear_bars', { track: 'Night breakbeat' });
const sections = [
  { name: 'First footsteps', kick: [0, 12], snare: [6, 18], hat: [2, 6, 10, 14, 18, 22], rim: [], velocity: 56 },
  { name: 'Night walk', kick: [0, 10, 12, 20], snare: [6, 18], hat: [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22], rim: [11, 23], velocity: 64 },
  { name: 'A second path', kick: [0, 10, 12, 16, 20], snare: [6, 18], hat: [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22], rim: [11, 23], velocity: 64 },
  { name: 'Homeward', kick: [0, 12, 20], snare: [6, 18], hat: [2, 6, 10, 14, 18, 22], rim: [], velocity: 55 },
];
for (let section = 0; section < sections.length; section++) {
  const s = sections[section];
  await call('write_drums', {
    track: 'Night breakbeat', start_bar: 1 + section * 8, bars: 8,
    pattern: { kick: row(s.kick, [0, 12]), snare: row(s.snare), hat: row(s.hat), clap: row(s.rim) },
    swing: 0, velocity: s.velocity, name: s.name,
  });
}
const analysis = await call('analyse_song');
if (analysis.problems.length) throw Error(`Song analysis: ${analysis.problems.join('; ')}`);
console.log(JSON.stringify({ project_id, tempo: analysis.tempo, length: analysis.length,
  harp_notes: harp.length, drum_sections: sections.map(s => s.name), warnings: analysis.warnings }));
await client.close();
JS
