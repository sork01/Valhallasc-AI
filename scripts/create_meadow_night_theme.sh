#!/bin/sh
# A separate, slower Greenmeadow theme with Chillhop accompaniment and no lead.
# Pass a project ID to revise/rerender this song instead of creating a new one.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
export MEADOW_NIGHT_ROOT="$ROOT"
export MEADOW_NIGHT_NEW_ID="${1:-}"
if [ -z "${DYB2_CHROME:-}" ]; then
  export DYB2_CHROME=/tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell
fi
cd "$ROOT/../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { mkdirSync, writeFileSync } from 'node:fs';
const reportDir = `${process.env.MEADOW_NIGHT_ROOT}/test-results/meadow-night-new`;
mkdirSync(reportDir, { recursive: true });
const client = new Client({ name: 'valhallasc-meadow-night-theme', version: '1' });
await client.connect(new StdioClientTransport({ command: process.execPath,
  args: ['--import', 'tsx', 'mcp/server.mjs'], cwd: process.cwd(), stderr: 'inherit',
  env: { ...process.env, DYB2_MCP_USER: 'codex' } }));
let project_id;
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: { ...(project_id ? { project_id } : {}), ...args } },
    undefined, { timeout: 900000 });
  if (result.isError) throw Error(`${name}: ${result.content.map(c => c.text).join('\n')}`);
  return JSON.parse(result.content[0].text);
}
const pc = pitch => {
  const [, name, accidental = ''] = /^([A-G])([#b]?)-?\d+$/.exec(pitch);
  return ({ C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 }[name] +
    (accidental === '#' ? 1 : accidental === 'b' ? -1 : 0) + 12) % 12;
};
const chords = {
  Gmaj7: { root: 'G2', fifth: 'D3', voicing: ['G3', 'B3', 'D4', 'F#4'] },
  'D7/F#': { root: 'F#2', fifth: 'A2', voicing: ['A3', 'C4', 'D4', 'F#4'] },
  Em7: { root: 'E2', fifth: 'B2', voicing: ['G3', 'B3', 'D4', 'E4'] },
  Cmaj7: { root: 'C2', fifth: 'G2', voicing: ['G3', 'B3', 'C4', 'E4'] },
  D6: { root: 'D2', fifth: 'A2', voicing: ['A3', 'B3', 'D4', 'F#4'] },
  D7: { root: 'D2', fifth: 'A2', voicing: ['A3', 'C4', 'D4', 'F#4'] },
  Bm7: { root: 'B1', fifth: 'F#2', voicing: ['A3', 'B3', 'D4', 'F#4'] },
  Am7: { root: 'A1', fifth: 'E2', voicing: ['G3', 'A3', 'C4', 'E4'] },
  G6: { root: 'G2', fifth: 'D3', voicing: ['G3', 'B3', 'D4', 'E4'] },
};
const progression = [
  'Gmaj7 D7/F# Em7 Cmaj7 Gmaj7 D6 Cmaj7 D7',
  'Em7 Bm7 Cmaj7 Gmaj7 Am7 D7 Gmaj7 D7',
  'Cmaj7 Gmaj7 Em7 D6 Am7 Em7 Cmaj7 D7',
  'Gmaj7 D6 Em7 Cmaj7 Am7 D7 Gmaj7 G6',
].join(' ').split(' ');
const sections = ['Familiar path', 'Lantern windows', 'Grass under moonlight', 'Home beneath the stars'];
const tracks = [
  { name: 'Warm keys', instrument: 'sork60', preset: 'Hiphop Chorus Keys', volume_db: -22, pan: -.12 },
  { name: 'Quiet motif', instrument: 'dexed', preset: 'MARIMBA', volume_db: -21, pan: .15 },
  { name: 'Night pad', instrument: 'sork60', preset: 'Mellow Pad', volume_db: -35, pan: -.08 },
  { name: 'Footstep bass', instrument: 'sorkbass2', preset: 'Fingered', volume_db: -2, pan: 0 },
  { name: 'Meadow Chillhop', instrument: 'axiom8', preset: 'Chillhop', volume_db: -8, pan: 0 },
];
try {
  if (process.env.MEADOW_NIGHT_NEW_ID) {
    project_id = process.env.MEADOW_NIGHT_NEW_ID;
    const project = await call('open_project');
    if (project.project_id !== project_id || project.name !== 'Valhalla Greenmeadow Night - The Meadow After Sundown')
      throw Error('Refusing to replace a different song');
    for (const track of tracks) await call('clear_bars', { track: track.name });
  } else {
    const created = await call('create_project', { name: 'Valhalla Greenmeadow Night - The Meadow After Sundown',
      bpm: 90, time_signature: '6/8', key: 'G major' });
    project_id = created.project_id;
    writeFileSync(`${reportDir}/project.json`, JSON.stringify(created, null, 2));
    console.log('PROJECT', JSON.stringify(created));
    for (const track of tracks) await call('add_track', track);
    await call('add_fx_return', { name: 'Short room', effect: 'sorkverb' });
  }
  for (const track of tracks) {
    await call('set_instrument', { track: track.name, instrument: track.instrument, preset: track.preset });
    await call('set_mix', { track: track.name, volume_db: track.volume_db, pan: track.pan });
  }
  await call('set_tempo', { bpm: 90 });
  for (const [track, level_db] of [['Warm keys', -24], ['Quiet motif', -22], ['Night pad', -27]])
    await call('set_send', { track, fx_return: 'Short room', level_db });
  for (const [parameter, value] of [['env.attack', .4], ['env.release', 1.1]])
    await call('automate', { track: 'Night pad', parameter, points: [{ bar: 1, value }, { bar: 33, value }] });
  // The keys preset's stock long release overlaps successive bar harmonies.
  for (const [parameter, value] of [['env.attack', .6], ['env.release', 1.2]])
    await call('automate', { track: 'Warm keys', parameter, points: [{ bar: 1, value }, { bar: 33, value }] });
  const grid = Object.fromEntries(tracks.map(t => [t.name, []]));
  const add = (track, pitch, beat, beats, velocity) => grid[track].push({ pitch, beat, beats, velocity });
  const answers = {
    Gmaj7: ['D4', 'B3', 'G3'], 'D7/F#': ['D4', 'C4', 'A3'], Em7: ['E4', 'D4', 'B3'],
    Cmaj7: ['E4', 'C4', 'B3'], D6: ['D4', 'B3', 'A3'], D7: ['F#4', 'D4', 'C4'],
    Bm7: ['F#4', 'D4', 'B3'], Am7: ['E4', 'C4', 'A3'], G6: ['E4', 'D4', 'B3'],
  };
  for (let bar = 0; bar < 32; bar++) {
    const chord = chords[progression[bar]], at = bar * 3;
    const home = bar >= 28, section = Math.floor(bar / 8);
    const velocity = home ? 48 : 54 + (bar % 4 === 0 ? 4 : 0);
    for (const pitch of chord.voicing) {
      add('Warm keys', pitch, at, home ? 1.3 : 1.15, velocity);
      if (bar !== 31) add('Warm keys', pitch, at + 1.5, .78, velocity - 9);
      if (section > 0) add('Night pad', pitch, at, 2.55, home ? 35 : 40);
    }
    add('Footstep bass', chord.root, at, home ? 2.5 : 1.25, home ? 64 : 72);
    add('Meadow Chillhop', 36, at, .2, home ? 66 : 76);
    add('Meadow Chillhop', 38, at + 1.5, .2, home ? 43 : 51);
    if (bar % 2 === 1 && bar !== 31) {
      add('Footstep bass', chord.fifth, at + 2.5, .32, 49);
      add('Meadow Chillhop', 36, at + 2.5, .2, 54);
    }
    const hats = section === 0 || home ? [.5, 1.5, 2.5] : [0, .5, 1, 1.5, 2, 2.5];
    for (const [i, beat] of hats.entries()) add('Meadow Chillhop', 42, at + beat, .14, 27 + (i % 2) * 8);
    // The source G–B–D–B is accompaniment: lower, rested, and much quieter than keys.
    if (progression[bar] === 'Gmaj7' && bar !== 30) {
      for (const [i, pitch] of ['G3', 'B3', 'D4', 'B3'].entries())
        add('Quiet motif', pitch, at + [.5, 1.5, 2, 2.5][i], .3, 49 - i * 3);
    } else if (bar % 2 === 0 || bar === 31) {
      for (const [i, pitch] of answers[progression[bar]].entries())
        add('Quiet motif', pitch, at + [.5, 1.5, 2][i], .34, home ? 35 - i * 3 : 43 - i * 3);
    } else if (section === 2) {
      add('Quiet motif', answers[progression[bar]][1], at + 1, .34, 38);
      add('Quiet motif', answers[progression[bar]][2], at + 2, .34, 34);
    }
  }
  // All pitched events, including root/fifth bass notes, must fit their exact bar chord.
  for (const [track, notes] of Object.entries(grid)) {
    if (track === 'Meadow Chillhop') continue;
    for (const note of notes) {
      const chord = chords[progression[Math.floor(note.beat / 3)]];
      const allowed = new Set([...chord.voicing, chord.root, chord.fifth].map(pc));
      if (!allowed.has(pc(note.pitch))) throw Error(`${track}: chord clash ${JSON.stringify(note)}`);
    }
  }
  for (let section = 0; section < 4; section++) {
    await call('add_marker', { name: sections[section], at_bar: section * 8 + 1 });
    for (const track of tracks) {
      const start = section * 24, end = start + 24;
      const notes = grid[track.name].filter(n => n.beat >= start && n.beat < end)
        .map(n => ({ ...n, beat: n.beat - start }));
      if (notes.length) await call('write_notes', { track: track.name, start_bar: section * 8 + 1,
        bars: 8, notes, name: sections[section] });
    }
  }
  const project = await call('get_project');
  if (project.bars !== 32 || project.meter !== '6/8') throw Error('Wrong arrangement length');
  const actual = {};
  for (const track of tracks) {
    actual[track.name] = [];
    for (let from_bar = 1; from_bar <= 32; from_bar += 8) {
      const view = await call('view_track', { track: track.name, from_bar, bars: 8, as: 'notes' });
      actual[track.name].push(...view.notes.map(n => ({ ...n, beat: n.beat + (from_bar - 1) * 3 })));
    }
    if (actual[track.name].length !== grid[track.name].length) throw Error(`Lost notes: ${track.name}`);
    if (track.instrument !== 'axiom8') {
      for (const note of actual[track.name]) {
        const chord = chords[progression[Math.floor(note.beat / 3)]];
        if (![...chord.voicing, chord.root, chord.fifth].map(pc).includes(pc(note.pitch)))
          throw Error(`Saved chord clash: ${track.name}, ${JSON.stringify(note)}`);
      }
    }
  }
  for (let bar = 0; bar < 32; bar++) {
    const drums = actual['Meadow Chillhop'];
    if (!drums.some(n => n.pitch === 'D2' && Math.abs(n.beat - (bar * 3 + 1.5)) < .001))
      throw Error(`Missing compound backbeat in bar ${bar + 1}`);
    for (const bass of actual['Footstep bass'].filter(n => Math.floor(n.beat / 3) === bar))
      if (!drums.some(n => n.pitch === 'C2' && Math.abs(n.beat - bass.beat) < .001))
        throw Error(`Unanchored bass in bar ${bar + 1}`);
  }
  const analysis = await call('analyse_song');
  writeFileSync(`${reportDir}/score.json`, JSON.stringify({ project_id, project, progression, grid: actual, analysis }, null, 2));
  if (analysis.problems.length) throw Error(JSON.stringify(analysis.problems));
  console.log('SCORE', JSON.stringify({ project_id, bars: project.bars, notes: Object.fromEntries(Object.entries(actual).map(([k,v]) => [k,v.length])), analysis }));
  const render = await call('render_audio', { path: '/tmp/valhallasc-meadow-night-new-dybase2.wav', per_track: true, tail_seconds: 3 });
  writeFileSync(`${reportDir}/render.json`, JSON.stringify(render, null, 2));
  console.log('RENDER', JSON.stringify(render));
  if (render.problems?.length || render.clipped_samples) throw Error('Repair render before export');
} finally {
  await client.close();
}
JS
