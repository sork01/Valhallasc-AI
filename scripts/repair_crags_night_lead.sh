#!/bin/sh
# Keep one chord-compatible, monophonic lead in the active Crags night project.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const project_id = '90d3be446ee5a58f';
const client = new Client({ name: 'valhallasc-crags-night-lead', version: '1' });
await client.connect(new StdioClientTransport({
  command: process.execPath, args: ['--import', 'tsx', 'mcp/server.mjs'],
  cwd: process.cwd(), stderr: 'inherit', env: { ...process.env, DYB2_MCP_USER: 'codex' },
}));
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: { project_id, ...args } }, undefined, { timeout: 300000 });
  if (result.isError) throw Error(`${name}: ${result.content.map(x => x.text).join('\n')}`);
  return JSON.parse(result.content[0].text);
}
const project = await call('open_project');
if (project.project_id !== project_id || project.tempo !== '92 bpm' || project.meter !== '4/4' || project.bars !== 32) {
  throw Error('The active Crags night project has changed; inspect it before editing.');
}
for (const track of ['Lead', 'Lead Snarl', 'Stabs', 'Arp']) {
  if (!project.tracks.some(t => t.name === track)) throw Error(`Missing track: ${track}`);
}

// The first and last lead phrases were copied over new chord progressions.
// These pitches follow each actual bar's chord while retaining the E-G motif,
// the phrase timings, and the rise/fall of the answer.
const pitches = {
  9: ['E5', 'G5', 'D5', 'E5'], 10: ['C5', 'A4', 'C5'],
  11: ['G4', 'B4', 'E5'], 12: ['D5', 'A4', 'C5', 'A4'],
  13: ['G5', 'D5', 'B4'], 14: ['A4', 'C5', 'E5'],
  15: ['D#5', 'B4', 'A4'], 16: ['B4', 'D5', 'E5'],
  17: ['B4', 'D5', 'E5'], 18: ['E5', 'C5', 'G4'],
  19: ['F5', 'E5', 'C5'], 20: ['B4', 'A4', 'F#4'],
  21: ['G4', 'B4', 'E5'], 22: ['D5', 'B4', 'G4'],
  23: ['C5', 'E5', 'G5'], 24: ['F#5', 'D#5', 'B4'],
  25: ['E5', 'G5', 'E5', 'C5'], 26: ['C5', 'A4', 'C5'],
  27: ['G4', 'B4', 'E5'], 28: ['D5', 'F#4', 'A4', 'C5'],
  29: ['E5', 'C5', 'B4'], 30: ['F#4', 'B4', 'D#5'],
  31: ['D5', 'B4', 'G4'], 32: ['E5'],
};
const notes = [];
for (const track of ['Lead', 'Lead Snarl']) {
  for (let from_bar = 1; from_bar <= 32; from_bar += 8) {
    const view = await call('view_track', { track, from_bar, bars: 8, as: 'notes' });
    for (const note of view.notes) notes.push({ ...note, beat: note.beat + (from_bar - 1) * 4 });
  }
}
notes.sort((a, b) => a.beat - b.beat);
if (notes.length !== 74) throw Error(`Expected 74 lead notes, found ${notes.length}`);
for (const [barText, wanted] of Object.entries(pitches)) {
  const bar = Number(barText);
  const current = notes.filter(n => Math.floor(n.beat / 4) + 1 === bar);
  if (current.length !== wanted.length) throw Error(`Bar ${bar}: expected ${wanted.length} notes, found ${current.length}`);
  for (let i = 0; i < current.length; i++) current[i].pitch = wanted[i];
}
for (let i = 1; i < notes.length; i++) {
  if (notes[i - 1].beat + notes[i - 1].beats > notes[i].beat) {
    throw Error(`Lead notes overlap at beat ${notes[i].beat}`);
  }
}
await call('write_notes', { track: 'Lead', start_bar: 1, bars: 32, name: 'Single ember melody', notes });
await call('remove_track', { track: 'Lead Snarl' });
await call('remove_track', { track: 'Stabs' });
await call('set_mix', { track: 'Lead', volume_db: -14, pan: 0.1 });
await call('set_mix', { track: 'Arp', volume_db: -18, pan: -0.25 });
const analysis = await call('analyse_song');
if (analysis.problems.length) throw Error(`Song analysis: ${analysis.problems.join('; ')}`);
console.log(JSON.stringify({ project_id, lead_notes: notes.length, lead_parts: 1,
  removed: ['Lead Snarl', 'Stabs'], warnings: analysis.warnings }));
await client.close();
JS
