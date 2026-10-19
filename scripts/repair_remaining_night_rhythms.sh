#!/bin/sh
# Repair the seven active night-remix projects still awaiting a timing pass.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const scores = [
  { zone: 'fen', id: '631d2ccf54a0ea32', bpm: 90, meter: '4/4', beats: 4,
    fixed: [['Lanterns', 64, { 0.75: 0.5 }], ['Strings', 12, { 0.25: 0 }]],
    melody: ['Flute', 68], pads: ['Pad', 'Strings'],
    break: { kick: [0, 14, 16, 22, 30], snare: [4, 12, 20, 28], hat: [2, 4, 6, 10, 12, 14, 18, 20, 22, 26, 28, 30], rim: [15, 31] } },
  { zone: 'city', id: '32550162e477d9e7', bpm: 90, meter: '3/4', beats: 3,
    fixed: [['Harp', 96, { 1.1: 1, 2.1: 2 }], ['Strings', 12, { 0.1: 0 }]],
    melody: ['Flute', 59], flute: true, pads: ['Pad', 'Strings'],
    break: { kick: [0, 12, 18], snare: [4, 16], hat: [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22], rim: [11, 23] } },
  { zone: 'wyrd', id: 'a2ac7b7ae8fa8ad8', bpm: 82, meter: '3/4', beats: 3,
    fixed: [['Arp', 96, { 0.1: 0, 1.15: 1, 2.15: 2 }], ['Strings', 12, { 0.25: 0 }], ['Bells', 5, { 2.15: 2 }]],
    melody: ['Flute', 52], flute: true, pads: ['Pad', 'Strings'],
    break: { kick: [0, 10, 12, 18], snare: [8, 20], hat: [2, 4, 6, 10, 14, 16, 18, 22], rim: [11, 23] } },
  { zone: 'sky', id: 'f8d95f2b7456bee1', bpm: 76, meter: '4/4', beats: 4,
    fixed: [['Arp', 96, { 3.25: 3.5 }], ['Strings', 12, { 0.35: 0 }]],
    melody: ['Flute', 52], flute: true, pads: ['Pad', 'Strings'],
    break: { kick: [0, 16, 22, 30], snare: [8, 24], hat: [0, 4, 6, 12, 16, 20, 22, 28], rim: [15, 31] } },
  { zone: 'nacre', id: 'f0c6df77cbbaed17', bpm: 90, meter: '6/8', beats: 3,
    fixed: [['Keys', 64, { 0.75: 0.5 }]], melody: ['Melody', 43], pads: ['Pad'],
    envelopes: { Keys: [0.03, 0.35], Melody: [0, 0.4] },
    break: { kick: [0, 10, 12, 20], snare: [6, 18], hat: [0, 4, 6, 10, 12, 16, 18, 22], rim: [11, 23] } },
  { zone: 'astral', id: 'c452ba1d09acef9f', bpm: 96, meter: '5/4', beats: 5,
    fixed: [['Wood', 64, { 0.8: 1, 3.2: 3 }]], melody: ['Melody', 53], pads: ['Strings'],
    envelopes: { Melody: [0.04, 0.35] },
    break: { kick: [0, 12, 20, 32], snare: [8, 28], hat: [0, 2, 4, 6, 8, 12, 14, 16, 18, 20, 22, 24, 26, 28, 32, 34, 36, 38], rim: [19, 39] } },
  { zone: 'prism', id: '5f35d1f41f52775f', bpm: 84, meter: '4/4', beats: 4,
    fixed: [['Salt glints', 64, { 0.85: 1, 2.75: 3 }]], melody: ['Mirage call', 48], pads: ['Mirror wash'],
    envelopes: { 'Mirage call': [0.04, 0.35] },
    break: { kick: [0, 6, 16, 26, 30], snare: [8, 24], hat: [1, 3, 5, 9, 11, 13, 17, 19, 21, 25, 27, 29], rim: [15, 31] } },
];
const client = new Client({ name: 'valhallasc-seven-night-rhythm-repairs', version: '1' });
await client.connect(new StdioClientTransport({
  command: process.execPath, args: ['--import', 'tsx', 'mcp/server.mjs'],
  cwd: process.cwd(), stderr: 'inherit', env: { ...process.env, DYB2_MCP_USER: 'codex' },
}));
async function call(name, args) {
  const result = await client.callTool({ name, arguments: args }, undefined, { timeout: 300000 });
  if (result.isError) throw Error(`${name}: ${result.content.map(x => x.text).join('\n')}`);
  return JSON.parse(result.content[0].text);
}
async function allNotes(score, track) {
  const notes = [];
  for (let from_bar = 1; from_bar <= 32; from_bar += 8) {
    const view = await call('view_track', { project_id: score.id, track, from_bar, bars: 8, as: 'notes' });
    notes.push(...view.notes.map(note => ({ ...note, beat: (from_bar - 1) * score.beats + note.beat })));
  }
  return notes;
}
async function rewrite(score, track, count, move, name) {
  const notes = await allNotes(score, track);
  if (notes.length !== count) throw Error(`${score.zone}/${track}: expected ${count} notes, found ${notes.length}`);
  const shifted = notes.map(note => ({ ...note, beat: move(note.beat) }));
  if (shifted.some(note => note.beat < 0 || note.beat >= 32 * score.beats)) throw Error(`${score.zone}/${track}: overrun`);
  await call('write_notes', { project_id: score.id, track, start_bar: 1, bars: 32, notes: shifted, name });
  return shifted.filter((note, i) => Math.abs(note.beat - notes[i].beat) > .001).length;
}
function row(length, hits, accents = [], ghosts = []) {
  const steps = Array(length).fill('.');
  for (const step of hits) {
    if (step >= length) throw Error(`Drum step ${step} exceeds ${length}`);
    steps[step] = accents.includes(step) ? 'X' : ghosts.includes(step) ? 'o' : 'x';
  }
  return steps.join('');
}
function sectionPattern(score, section) {
  const length = score.beats * 8;
  const b = score.break;
  const main = section === 1 || section === 2;
  const kick = main ? b.kick : section === 0 ? b.kick.filter(s => s === 0 || s === length / 2) : b.kick.filter(s => s === 0 || s === length / 2 || s >= length - 2);
  const hat = main ? b.hat : b.hat.filter((_, i) => i % 2 === (section === 0 ? 0 : 1));
  const rim = main ? b.rim : [];
  return { kick: row(length, kick, [0, length / 2]), snare: row(length, b.snare), hat: row(length, hat), clap: row(length, rim, [], rim) };
}
for (const score of scores) {
  if (process.env.ZONES && !process.env.ZONES.split(',').includes(score.zone)) continue;
  const project = await call('open_project', { project_id: score.id });
  if (project.project_id !== score.id || project.tempo !== `${score.bpm} bpm` || project.meter !== score.meter || project.bars !== 32)
    throw Error(`${score.zone}: the active project changed; inspect it before editing`);
  const count = {};
  for (const [track, expected, positions] of score.fixed) {
    if (!project.tracks.some(t => t.name === track)) throw Error(`${score.zone}: missing ${track}`);
    count[track] = await rewrite(score, track, expected, beat => {
      const bar = Math.floor(beat / score.beats), within = +(beat - bar * score.beats).toFixed(3);
      const target = positions[within] ?? within;
      if (Math.abs(target - within) > .5) throw Error(`${score.zone}/${track}: unexpected shift ${within} -> ${target}`);
      return bar * score.beats + target;
    }, `${track} on the ${score.meter} grid`);
  }
  const [melody, expected] = score.melody;
  count[melody] = await rewrite(score, melody, expected, beat => Math.round(beat * 2) / 2, `${melody} on the eighth-note grid`);
  if (score.flute) await call('set_instrument', { project_id: score.id, track: melody, instrument: 'dexed', preset: 'WHISTLE FLUTE' });
  for (const track of score.pads) {
    for (const [parameter, value] of [['env.attack', .08], ['env.release', .45]])
      await call('automate', { project_id: score.id, track, parameter, points: [{ bar: 1, value }, { bar: 33, value }] });
  }
  for (const [track, [attack, release]] of Object.entries(score.envelopes || {})) {
    for (const [parameter, value] of [['env.attack', attack], ['env.release', release]])
      await call('automate', { project_id: score.id, track, parameter, points: [{ bar: 1, value }, { bar: 33, value }] });
  }
  await call('clear_bars', { project_id: score.id, track: 'Night breakbeat' });
  for (let section = 0; section < 4; section++) {
    await call('write_drums', { project_id: score.id, track: 'Night breakbeat',
      start_bar: 1 + section * 8, bars: 8, pattern: sectionPattern(score, section),
      swing: 0, velocity: section === 0 ? 54 : section === 3 ? 53 : 62,
      name: ['First footsteps', 'Night walk', 'A second path', 'Homeward'][section] });
  }
  const analysis = await call('analyse_song', { project_id: score.id });
  if (analysis.problems.length) throw Error(`${score.zone}: ${analysis.problems.join('; ')}`);
  console.log(JSON.stringify({ zone: score.zone, project_id: score.id, bpm: score.bpm, meter: score.meter,
    moved: count, warnings: analysis.warnings }));
}
await client.close();
JS
