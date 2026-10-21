#!/bin/sh
# Greenmeadow After Hours: approved instrument lineup, swung 1990s hip-hop.
# MODE=inspect reads the active project; MODE=render only rerenders it.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
export MEADOW_NIGHT_ROOT="$ROOT"
export DYB2_CHROME="${DYB2_CHROME:-/tmp/valhallasc-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell}"
cd "$ROOT/../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
const root = process.env.MEADOW_NIGHT_ROOT;
const directory = `${root}/test-results/meadow-night-hiphop`;
mkdirSync(directory, { recursive: true });
const project_id = '0d47202bc633294a';
const client = new Client({ name: 'meadow-after-hours', version: '1' });
await client.connect(new StdioClientTransport({ command: process.execPath,
  args: ['--import', 'tsx', 'mcp/server.mjs'], cwd: process.cwd(), stderr: 'inherit',
  env: { ...process.env, DYB2_MCP_USER: 'codex' } }));
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: { project_id, ...args } }, undefined, { timeout: 900000 });
  if (result.isError || result.content.some(c => c.text?.startsWith('WARNING:'))) throw Error(`${name}: ${JSON.stringify(result.content)}`);
  return JSON.parse(result.content[0].text);
}
const pc = pitch => {
  if (typeof pitch === 'number') return pitch % 12;
  const [, letter, accidental = ''] = /^([A-G])([#b]?)-?\d+$/.exec(pitch);
  return ({ C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 }[letter] +
    (accidental === '#' ? 1 : accidental === 'b' ? -1 : 0) + 12) % 12;
};
// A shared 60:40 eighth-note feel: quarter-note backbeats stay fixed. Subdivide
// each long/short eighth for occasional sixteenth pickups, in every instrument.
const swing = beat => {
  const whole = Math.floor(beat), fraction = beat - whole;
  return whole + (fraction <= .5 ? fraction * 1.2 : .6 + (fraction - .5) * .8);
};
const chords = {
  Gmaj9: { root: 'G2', fifth: 'D3', voices: ['B3', 'D4', 'F#4', 'A4'], answer: ['D4', 'B3', 'A3'] },
  'G6/9': { root: 'G2', fifth: 'D3', voices: ['A3', 'B3', 'D4', 'E4'], answer: ['E4', 'D4', 'B3'] },
  Am9: { root: 'A2', fifth: 'E3', voices: ['G3', 'B3', 'C4', 'E4'], answer: ['E4', 'C4', 'B3'] },
  D13: { root: 'D2', fifth: 'A2', voices: ['F#3', 'B3', 'C4', 'E4'], answer: ['E4', 'C4', 'B3'] },
  Bm7: { root: 'B1', fifth: 'F#2', voices: ['A3', 'B3', 'D4', 'F#4'], answer: ['F#4', 'D4', 'B3'] },
  E7b9: { root: 'E2', fifth: 'B2', voices: ['G#3', 'B3', 'D4', 'F4'], answer: ['D4', 'B3', 'G#3'] },
  Em9: { root: 'E2', fifth: 'B2', voices: ['G3', 'B3', 'D4', 'F#4'], answer: ['E4', 'D4', 'B3'] },
  A13: { root: 'A1', fifth: 'E2', voices: ['G3', 'B3', 'C#4', 'F#4'], answer: ['E4', 'C#4', 'B3'] },
  Cmaj9: { root: 'C2', fifth: 'G2', voices: ['G3', 'B3', 'D4', 'E4'], answer: ['E4', 'D4', 'B3'] },
  Cm6: { root: 'C2', fifth: 'G2', voices: ['Eb3', 'G3', 'A3', 'C4'], answer: ['Eb4', 'C4', 'A3'] },
};
const progression = [
  'Gmaj9 Gmaj9 Am9 D13 Bm7 E7b9 Am9 D13',
  'G6/9 Bm7 Em9 A13 Am9 D13 Gmaj9 D13',
  'Cmaj9 Cm6 Bm7 E7b9 Am9 D13 G6/9 D13',
  'Gmaj9 Bm7 Em9 A13 Am9 D13 G6/9 G6/9',
].join(' ').split(' ');
const sections = ['Familiar streets', 'Window light', 'Bossa under the trees', 'Home on the last beat'];
const tracks = [
  { name: 'Electric piano', instrument: 'dexed', preset: 'TINE PIANO', volume_db: -16, pan: -.08 },
  { name: 'Wood bass', instrument: 'dexed', preset: 'WOOD BASS', volume_db: -11, pan: 0 },
  { name: 'Quiet marimba', instrument: 'dexed', preset: 'MARIMBA', volume_db: -8, pan: .2 },
  { name: 'Night pad', instrument: 'sork60', preset: 'Mellow Pad', volume_db: -36, pan: -.15 },
  { name: 'Boom bap drums', instrument: 'axiom8', preset: 'Hip-hop', volume_db: -7, pan: 0 },
  { name: 'Soft hats', instrument: 'axiom8', preset: 'Chillhop', volume_db: 0, pan: .1 },
];
async function readGrid(project) {
  const beats = Number(project.meter.split('/')[0]) * 4 / Number(project.meter.split('/')[1]);
  const grid = {};
  for (const track of project.tracks.filter(t => t.instrument)) {
    grid[track.name] = [];
    for (let from_bar = 1; from_bar <= project.bars; from_bar += 8) {
      const data = await call('view_track', { track: track.name, from_bar,
        bars: Math.min(8, project.bars - from_bar + 1), as: 'notes' });
      grid[track.name].push(...data.notes.map(n => ({ ...n, beat: n.beat + (from_bar - 1) * beats })));
    }
  }
  return grid;
}
function checkGrid(grid) {
  for (const [name, notes] of Object.entries(grid)) {
    if (['Boom bap drums', 'Soft hats'].includes(name)) continue;
    for (const note of notes) {
      const c = chords[progression[Math.floor(note.beat / 4)]];
      if (!c || ![...c.voices, c.root, c.fifth].map(pc).includes(pc(note.pitch)))
        throw Error(`Chord clash: ${name} ${JSON.stringify(note)}`);
      if (note.beat + note.beats > (Math.floor(note.beat / 4) + 1) * 4 + .01)
        throw Error(`Note carries across chord boundary: ${name}`);
    }
  }
  const drums = grid['Boom bap drums'];
  if (drums.some(n => !['C2', 'D2', 36, 38].includes(n.pitch))) throw Error('Hip-hop hat is forbidden');
  for (let bar = 0; bar < 32; bar++) {
    for (const beat of [1, 3])
      if (!drums.some(n => ['D2', 38].includes(n.pitch) && Math.abs(n.beat - (bar * 4 + beat)) < .01))
        throw Error(`Missing backbeat in bar ${bar + 1}`);
    for (const bass of grid['Wood bass'].filter(n => Math.floor(n.beat / 4) === bar))
      if (!drums.some(n => ['C2', 36].includes(n.pitch) && Math.abs(n.beat - bass.beat) < .01))
        throw Error(`Unanchored bass: bar ${bar + 1}`);
  }
}
try {
  const before = await call('open_project');
  if (before.project_id !== project_id || !before.name.startsWith('Valhalla Greenmeadow Night - '))
    throw Error('Wrong active project');
  if (process.env.MODE !== 'render') {
    const beforeGrid = await readGrid(before);
    const inspected = { project: before, grid: beforeGrid, analysis: await call('analyse_song') };
    const file = process.env.MODE === 'inspect' ? 'inspection.json' : 'before-rework.json';
    if (process.env.MODE === 'inspect' || !existsSync(`${directory}/${file}`))
      writeFileSync(`${directory}/${file}`, JSON.stringify(inspected, null, 2));
    console.log('INSPECTED', JSON.stringify({ name: before.name, tempo: before.tempo, meter: before.meter,
      bars: before.bars, tracks: before.tracks.map(t => ({ name: t.name, instrument: t.instrument, notes: t.notes })) }));
    if (process.env.MODE === 'inspect') {
      console.log('PRESETS', JSON.stringify(await call('list_presets', { instrument: 'dexed', query: 'piano' })));
    } else {
      // Rebuild tracks in the active project, after inspecting and archiving its
      // complete current grid. No daytime project or older night draft is edited.
      for (const t of before.tracks) await call('remove_track', { track: t.name });
      for (const marker of before.markers) {
        const name = marker.replace(/^bar [\d.]+: /, '');
        if (!name.startsWith('Key:')) await call('remove_marker', { name });
      }
      await call('rename_project', { name: 'Valhalla Greenmeadow Night - Greenmeadow After Hours' });
      await call('set_time_signature', { numerator: 4, denominator: 4 });
      await call('set_tempo', { bpm: 82 });
      for (const track of tracks) await call('add_track', track);
      await call('add_fx_return', { name: 'Small room', effect: 'sorkverb' });
      for (const [track, level_db] of [['Electric piano', -22], ['Quiet marimba', -24], ['Night pad', -30]])
        await call('set_send', { track, fx_return: 'Small room', level_db });
      for (const [parameter, value] of [['env.attack', .4], ['env.release', 1.1]])
        await call('automate', { track: 'Night pad', parameter, points: [{ bar: 1, value }, { bar: 33, value }] });
      await call('automate', { track: 'Soft hats', parameter: 'hatLevel',
        points: [{ bar: 1, value: 6 }, { bar: 33, value: 6 }] });
      await call('add_effect', { track: 'Electric piano', effect: 'sorkcrush' });
      // Gentle hiss is the approved texture, not recorded vinyl crackles. Keep
      // full sample rate and bit depth; no tape wow, pitch drift or crushed mix.
      for (const [parameter, value] of [['bits', 24], ['rate', 48000], ['mix', 50], ['noise', 50],
        ['jitter', 0], ['dither', 0], ['drive', 0], ['cutoff', 12000], ['output', 0]])
        await call('automate', { track: 'Electric piano', effect: 'sorkcrush', parameter,
          points: [{ bar: 1, value }, { bar: 33, value }] });
      await call('automate', { track: 'Electric piano', effect: 'sorkcrush', parameter: 'noise',
        points: [{ bar: 1, value: 50 }, { bar: 32.5, value: 50 }, { bar: 33, value: 0 }] });
      const grid = Object.fromEntries(tracks.map(t => [t.name, []]));
      const add = (track, pitch, beat, beats, velocity) => grid[track].push({ pitch, beat, beats, velocity });
      const bassTimes = [[0, 2.5], [0, 2], [0, 2.5, 3.5], [0, 1.75, 2.5]];
      const extraKicks = [[1.5], [.75], [], []];
      for (let bar = 0; bar < 32; bar++) {
        const chord = chords[progression[bar]], at = bar * 4, section = Math.floor(bar / 8);
        const ending = bar >= 28, last = bar === 31;
        // Bossa-style chord anticipation against a firm two-and-four snare.
        const comp = last ? [[0, 3.45]] : section === 2
          ? [[0, .95], [1.5, .48], [2.75, .65]]
          : [[0, 1.1], [1.5, .52], [3, .55]];
        for (const [hit, length] of comp) for (const [voice, pitch] of chord.voices.entries())
          add('Electric piano', pitch, at + swing(hit) + voice * .006, length,
            (ending ? 58 : 65) - voice * 2 - (hit > 0 ? 7 : 0) + (bar % 4 === 0 ? 2 : 0));
        if (section > 0) for (const pitch of chord.voices)
          add('Night pad', pitch, at, 3.55, ending ? 33 : 38);
        const times = last ? [0] : bassTimes[bar % 4];
        for (const [i, beat] of times.entries()) {
          const position = swing(beat), next = times[i + 1] === undefined ? 4 : swing(times[i + 1]);
          const duration = Math.min(i === 0 ? 1.35 : .65, next - position - .12);
          add('Wood bass', i % 2 === 0 ? chord.root : chord.fifth, at + position,
            last ? 3.4 : duration, i === 0 ? 77 : 61);
          add('Boom bap drums', 36, at + position, .17, i === 0 ? 87 : 69);
        }
        if (!ending) for (const beat of extraKicks[bar % 4])
          add('Boom bap drums', 36, at + swing(beat), .17, 58);
        for (const [beat, velocity] of [[1, 79], [3, 85]])
          add('Boom bap drums', 38, at + beat, .17, velocity - (section === 0 || ending ? 7 : 0));
        if (section === 1 || section === 2)
          add('Boom bap drums', 38, at + swing(2.75), .12, 26 + bar % 3 * 3);
        const hats = ending ? [.5, 1.5, 2.5, 3.5] : [0, .5, 1, 1.5, 2, 2.5, 3, 3.5];
        for (const [i, beat] of hats.entries()) {
          if (bar === 0 && beat === 0) continue; // the first kick gets space before the swung hat
          add('Soft hats', 42, at + swing(beat), .11, i % 2 === 0 ? 62 : 76);
        }
        if (!ending && bar % 2 === 1) add('Soft hats', 42, at + swing(.75), .1, 49);
        if (bar % 8 === 7 && !last) add('Soft hats', 46, at + swing(3.5), .19, 29);
        if (['Gmaj9', 'G6/9'].includes(progression[bar]) && !last) {
          for (const [i, pitch] of ['G3', 'B3', 'D4', 'B3'].entries())
            add('Quiet marimba', pitch, at + swing([.5, 1, 2.5, 3.5][i]), .28, 46 - i * 3);
        } else if (bar % 2 === 0 && !ending) {
          for (const [i, pitch] of chord.answer.entries())
            add('Quiet marimba', pitch, at + swing([1.5, 2.5, 3][i]), .3, 39 - i * 3);
        } else if (section === 2 || last) {
          for (const [i, pitch] of chord.answer.slice(1).entries())
            add('Quiet marimba', pitch, at + swing([1.5, 2.5][i]), .32, 34 - i * 3);
        }
      }
      checkGrid(grid);
      for (let section = 0; section < 4; section++) {
        await call('add_marker', { name: sections[section], at_bar: section * 8 + 1 });
        const start = section * 32;
        for (const track of tracks) {
          const notes = grid[track.name].filter(n => n.beat >= start && n.beat < start + 32)
            .map(n => ({ ...n, beat: n.beat - start }));
          if (notes.length) await call('write_notes', { track: track.name, start_bar: section * 8 + 1,
            bars: 8, notes, name: sections[section] });
        }
      }
    }
  }
  if (process.env.MODE !== 'inspect') {
    // Fader edits for a render pass stay in the editable source of truth.
    if (process.env.MEADOW_MIX) for (const [track, volume_db] of Object.entries(JSON.parse(process.env.MEADOW_MIX)))
      await call('set_mix', { track, volume_db });
    const project = await call('get_project');
    if (project.bars !== 32 || project.meter !== '4/4' || project.tempo !== '82 bpm') throw Error('Wrong arrangement');
    const grid = await readGrid(project);
    checkGrid(grid);
    const analysis = await call('analyse_song');
    writeFileSync(`${directory}/score.json`, JSON.stringify({ project_id, project, progression,
      swing: '60:40 eighths, shared by drums, bass, piano and marimba', grid, analysis }, null, 2));
    console.log('SCORE', JSON.stringify({ project_id, bars: project.bars,
      notes: Object.fromEntries(Object.entries(grid).map(([name, notes]) => [name, notes.length])), analysis }));
    if (analysis.problems.length) throw Error(JSON.stringify(analysis.problems));
    const render = await call('render_audio', { path: '/tmp/valhallasc-meadow-night-hiphop-dybase2.wav',
      per_track: true, tail_seconds: 3 });
    writeFileSync(`${directory}/render.json`, JSON.stringify(render, null, 2));
    console.log('RENDER', JSON.stringify(render));
    if (render.problems?.length || render.clipped_samples) throw Error('Repair render before export');
  }
} finally { await client.close(); }
JS
