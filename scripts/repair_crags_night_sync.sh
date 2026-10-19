#!/bin/sh
# Tighten the active Crags night project's full rhythm section and chord changes.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const project_id = '90d3be446ee5a58f';
const client = new Client({ name: 'valhallasc-crags-night-sync', version: '1' });
await client.connect(new StdioClientTransport({
  command: process.execPath, args: ['--import', 'tsx', 'mcp/server.mjs'],
  cwd: process.cwd(), stderr: 'inherit', env: { ...process.env, DYB2_MCP_USER: 'codex' },
}));
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: { project_id, ...args } }, undefined, { timeout: 300000 });
  if (result.isError) throw Error(`${name}: ${result.content.map(x => x.text).join('\n')}`);
  return JSON.parse(result.content[0].text);
}
async function allNotes(track) {
  const notes = [];
  for (let from_bar = 1; from_bar <= 32; from_bar += 8) {
    const view = await call('view_track', { track, from_bar, bars: 8, as: 'notes' });
    for (const note of view.notes) notes.push({ ...note, beat: note.beat + (from_bar - 1) * 4 });
  }
  return notes.sort((a, b) => a.beat - b.beat);
}
function row(hits, accents = []) {
  const steps = Array(32).fill('.');
  for (const step of hits) steps[step] = accents.includes(step) ? 'X' : 'x';
  return steps.join('');
}

const project = await call('open_project');
if (project.project_id !== project_id || project.tempo !== '92 bpm' || project.meter !== '4/4' || project.bars !== 32) {
  throw Error('The active Crags project has changed; inspect it before editing.');
}
for (const track of ['Bass', 'Arp', 'Lead', 'Pad', 'Night breakbeat']) {
  if (!project.tracks.some(t => t.name === track)) throw Error(`Missing track: ${track}`);
}

// Bass already hits 1 and 3& in every bar. Give both hits the same kick anchor.
// Every snare stays on beat 3; all variations now use eighth-note positions.
await call('clear_bars', { track: 'Night breakbeat' });
const sections = [
  { name: 'First footsteps, locked', kick: [0, 10, 16, 26], hat: [2, 6, 10, 14, 18, 22, 26, 30], velocity: 55 },
  { name: 'Night walk, locked', kick: [0, 6, 10, 16, 26, 30], hat: [2, 4, 6, 10, 12, 14, 18, 20, 22, 26, 28, 30], velocity: 61 },
  { name: 'A second path, locked', kick: [0, 10, 16, 22, 26], hat: [2, 4, 6, 10, 12, 14, 18, 20, 22, 26, 28, 30], velocity: 61 },
  { name: 'Homeward, locked', kick: [0, 10, 16, 26], hat: [2, 6, 10, 14, 18, 22, 26, 30], velocity: 54 },
];
for (let section = 0; section < sections.length; section++) {
  const s = sections[section];
  await call('write_drums', {
    track: 'Night breakbeat', start_bar: 1 + section * 8, bars: 8,
    pattern: { kick: row(s.kick, [0, 16]), snare: row([8, 24]), hat: row(s.hat) },
    swing: 0, velocity: s.velocity, name: s.name,
  });
}

// The lead had stray sixteenth-note starts (.25 and .75 within a beat) among
// its otherwise straight eighth-note calls. Keep the pitches and phrase order.
const lead = await allNotes('Lead');
if (lead.length !== 74) throw Error(`Expected 74 lead notes, found ${lead.length}`);
let moved = 0;
for (const note of lead) {
  const beatInBar = note.beat % 4;
  const target = Number.isInteger(beatInBar * 2) ? beatInBar : Math.floor(beatInBar) + .5;
  if (Math.abs(target - beatInBar) > 1e-6) {
    note.beat += target - beatInBar;
    moved++;
  }
}
lead.sort((a, b) => a.beat - b.beat);
for (let i = 1; i < lead.length; i++) {
  if (lead[i - 1].beat + lead[i - 1].beats > lead[i].beat + 1e-6) {
    throw Error(`Lead overlap after grid correction at beat ${lead[i].beat}`);
  }
}
await call('write_notes', { track: 'Lead', start_bar: 1, bars: 32, name: 'Ember melody on eighths', notes: lead });

// This Sork-60 pad had a very slow attack and a long release, so each chord
// arrived after the bass and bled into the next chord. Keep the preset, but
// tighten its envelope and shorten each chord slightly before the next bar.
const pad = await allNotes('Pad');
if (pad.length !== 128 || pad.some(n => n.beat % 4 !== 0 || n.beats !== 4)) {
  throw Error('Pad chord structure changed; inspect it before shortening.');
}
for (const note of pad) note.beats = 3.75;
await call('write_notes', { track: 'Pad', start_bar: 1, bars: 32, name: 'Ridge afterglow, clear changes', notes: pad });
await call('automate', { track: 'Pad', parameter: 'env.attack', points: [{ bar: 1, value: .6 }] });
await call('automate', { track: 'Pad', parameter: 'env.release', points: [{ bar: 1, value: 1.5 }] });
await call('set_send', { track: 'Pad', fx_return: 'Reverb', level_db: -18 });
await call('set_send', { track: 'Lead', fx_return: 'Reverb', level_db: -18 });

const analysis = await call('analyse_song');
if (analysis.problems.length) throw Error(`Song analysis: ${analysis.problems.join('; ')}`);
console.log(JSON.stringify({ project_id, moved_lead_notes: moved, lead_notes: lead.length,
  pad_notes: pad.length, groove: sections.map(s => s.name), warnings: analysis.warnings }));
await client.close();
JS
