#!/bin/sh
# Repair the active Rimeveil night score on its native 88 BPM, 6/8 grid.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const project_id = '4091d2184af5bf68';
const client = new Client({ name: 'valhallasc-rime-night-rhythm', version: '1' });
await client.connect(new StdioClientTransport({
  command: process.execPath, args: ['--import', 'tsx', 'mcp/server.mjs'],
  cwd: process.cwd(), stderr: 'inherit', env: { ...process.env, DYB2_MCP_USER: 'codex' },
}));
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: { project_id, ...args } }, undefined, { timeout: 300000 });
  if (result.isError) throw Error(`${name}: ${result.content.map(x => x.text).join('\n')}`);
  return JSON.parse(result.content[0].text);
}
function row(hits, accents = [], ghosts = []) {
  const steps = Array(24).fill('.'); // two 6/8 bars, sixteenth-note resolution
  for (const step of hits) steps[step] = accents.includes(step) ? 'X' : ghosts.includes(step) ? 'o' : 'x';
  return steps.join('');
}

const project = await call('open_project');
if (project.project_id !== project_id || project.tempo !== '88 bpm' || project.meter !== '6/8' || project.bars !== 32)
  throw Error('The active Rimeveil night project has changed; inspect it before editing.');
for (const track of ['Bells', 'Pad', 'Bass', 'Lead', 'Strings', 'Night breakbeat'])
  if (!project.tracks.some(t => t.name === track)) throw Error(`Missing track: ${track}`);

// Each bell was a sixteenth late. Keep its three-note per-bar figure and pitch,
// but put the attacks on the quarter-note cross-rhythm it was written for.
const bells = [];
for (let from_bar = 1; from_bar <= 32; from_bar += 8) {
  const view = await call('view_track', { track: 'Bells', from_bar, bars: 8, as: 'notes' });
  for (const note of view.notes) {
    const local = +(note.beat % 3).toFixed(3);
    if (![0.25, 1.25, 2.25, 0, 1, 2].includes(local)) throw Error(`Unexpected bell beat ${note.beat}`);
    bells.push({ ...note, beat: (from_bar - 1) * 3 + note.beat - (local % 1) });
  }
}
if (bells.length !== 96) throw Error(`Expected 96 bell notes, found ${bells.length}`);
await call('write_notes', { track: 'Bells', start_bar: 1, bars: 32, notes: bells, name: 'Falling ice steps on the pulse' });

// The lead's scattered fractional starts were not a repeatable swing pattern.
// Quantize attacks to the 6/8 eighth-note grid, preserving notes and phrasing.
const lead = [];
for (let from_bar = 1; from_bar <= 32; from_bar += 8) {
  const view = await call('view_track', { track: 'Lead', from_bar, bars: 8, as: 'notes' });
  for (const note of view.notes) {
    const beat = (from_bar - 1) * 3 + Math.round(note.beat * 2) / 2;
    if (beat >= 96) throw Error(`Lead overruns the loop at beat ${beat}`);
    lead.push({ ...note, beat });
  }
}
if (lead.length !== 72) throw Error(`Expected 72 lead notes, found ${lead.length}`);
await call('write_notes', { track: 'Lead', start_bar: 1, bars: 32, notes: lead, name: 'Climbing stars and falling answer on the eighths' });

// The original pad and strings presets have 5.0 s and 4.2 s attacks: their
// audible chords arrive several bars after MIDI beat one. Make those attacks
// prompt while retaining the same Sork-60 timbres and a short shared tail.
for (const track of ['Pad', 'Strings']) {
  await call('automate', { track, parameter: 'env.attack', points: [{ bar: 1, value: 0.08 }, { bar: 33, value: 0.08 }] });
  await call('automate', { track, parameter: 'env.release', points: [{ bar: 1, value: 0.5 }, { bar: 33, value: 0.5 }] });
}

// A restrained compound-meter break: kick on the first dotted quarter,
// snare on the second, with a few consistent eighth-note kick pickups.
// It stays distinct from the straight 4/4 Crags and 6/8 Meadow breaks.
await call('clear_bars', { track: 'Night breakbeat' });
const sections = [
  { name: 'First footsteps', kick: [0, 12], snare: [6, 18], hat: [0, 4, 8, 12, 16, 20], rim: [], velocity: 52 },
  { name: 'Night walk', kick: [0, 10, 12, 22], snare: [6, 18], hat: [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22], rim: [11, 23], velocity: 61 },
  { name: 'A second path', kick: [0, 10, 12, 20], snare: [6, 18], hat: [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22], rim: [11, 23], velocity: 62 },
  { name: 'Homeward', kick: [0, 12, 22], snare: [6, 18], hat: [2, 6, 10, 14, 18, 22], rim: [], velocity: 52 },
];
for (let section = 0; section < sections.length; section++) {
  const s = sections[section];
  await call('write_drums', {
    track: 'Night breakbeat', start_bar: 1 + section * 8, bars: 8, name: s.name,
    pattern: { kick: row(s.kick, [0, 12]), snare: row(s.snare), hat: row(s.hat), clap: row(s.rim, [], s.rim) },
    swing: 0, velocity: s.velocity,
  });
}
const analysis = await call('analyse_song');
if (analysis.problems.length) throw Error(`Song analysis: ${analysis.problems.join('; ')}`);
console.log(JSON.stringify({ project_id, tempo: analysis.tempo, length: analysis.length,
  bells: bells.length, lead: lead.length, break_sections: sections.map(s => s.name), warnings: analysis.warnings }));
await client.close();
JS
