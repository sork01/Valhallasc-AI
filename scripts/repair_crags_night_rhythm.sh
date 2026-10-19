#!/bin/sh
# Correct the active Emberfall Crags night project at its native 92 BPM, 4/4 grid.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const project_id = '90d3be446ee5a58f';
const client = new Client({ name: 'valhallasc-crags-night-rhythm', version: '1' });
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
  const steps = Array(32).fill('.'); // two 4/4 bars at sixteenth-note resolution
  for (const step of hits) steps[step] = accents.includes(step) ? 'X' : 'x';
  return steps.join('');
}

const project = await call('open_project');
if (project.project_id !== project_id || project.tempo !== '92 bpm' || project.meter !== '4/4' || project.bars !== 32) {
  throw Error('The active Crags night project has changed; inspect it before editing.');
}
for (const track of ['Bass', 'Arp', 'Lead', 'Pad', 'Night breakbeat']) {
  if (!project.tracks.some(t => t.name === track)) throw Error(`Missing track: ${track}`);
}

// The three plucks in each bar landed a sixteenth after the intended pulse.
// Place them at beat 1&, beat 2&, and beat 4; retain the pitches, dynamics,
// sparse spacing, and the song's other intentional melody pickups.
const arp = [];
for (let from_bar = 1; from_bar <= 32; from_bar += 8) {
  const view = await call('view_track', { track: 'Arp', from_bar, bars: 8, as: 'notes' });
  for (const note of view.notes) {
    const bar = Math.floor(note.beat / 4);
    const within = +(note.beat - bar * 4).toFixed(3);
    const target = Math.abs(within - .75) < .001 ? .5
      : Math.abs(within - 1.75) < .001 ? 1.5
      : Math.abs(within - 3.25) < .001 ? 3
      : [.5, 1.5, 3].includes(within) ? within : null;
    if (target === null) throw Error(`Unexpected pluck timing: bar ${from_bar + bar}, beat ${within}`);
    arp.push({ ...note, beat: (from_bar - 1 + bar) * 4 + target });
  }
}
if (arp.length !== 96) throw Error(`Expected 96 plucks, found ${arp.length}`);
await call('write_notes', { track: 'Arp', start_bar: 1, bars: 32, name: 'Offbeat sparks in 4/4', notes: arp });

// Keep a restrained, two-bar half-time Chillhop break. Both bars have a kick
// on beat 1 and a snare on beat 3. The second half adds a different kick
// answer; no swung note is pushed off the sixteenth-note grid.
await call('clear_bars', { track: 'Night breakbeat' });
const sections = [
  { name: 'First footsteps', kick: [0, 16], snare: [8, 24], hat: [2, 6, 10, 14, 18, 22, 26, 30], rim: [], velocity: 56 },
  { name: 'Night walk', kick: [0, 6, 16, 22, 30], snare: [8, 24], hat: [2, 4, 6, 10, 12, 14, 18, 20, 22, 26, 28, 30], rim: [15, 31], velocity: 63 },
  { name: 'A second path', kick: [0, 6, 16, 20, 30], snare: [8, 24], hat: [2, 4, 6, 10, 12, 14, 18, 20, 22, 26, 28, 30], rim: [15, 31], velocity: 64 },
  { name: 'Homeward', kick: [0, 16, 30], snare: [8, 24], hat: [2, 6, 10, 14, 18, 22, 26, 30], rim: [], velocity: 55 },
];
for (let section = 0; section < sections.length; section++) {
  const s = sections[section];
  await call('write_drums', {
    track: 'Night breakbeat', start_bar: 1 + section * 8, bars: 8,
    pattern: { kick: row(s.kick, [0, 16]), snare: row(s.snare), hat: row(s.hat), clap: row(s.rim) },
    swing: 0, velocity: s.velocity, name: s.name,
  });
}
const analysis = await call('analyse_song');
if (analysis.problems.length) throw Error(`Song analysis: ${analysis.problems.join('; ')}`);
console.log(JSON.stringify({ project_id, tempo: analysis.tempo, length: analysis.length,
  pluck_notes: arp.length, drum_sections: sections.map(s => s.name), warnings: analysis.warnings }));
await client.close();
JS
