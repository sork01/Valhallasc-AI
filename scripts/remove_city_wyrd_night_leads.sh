#!/bin/sh
# Keep the source rise in the accompaniment, then remove each foreground flute.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const client = new Client({ name: 'valhallasc-city-wyrd-no-lead', version: '1' });
await client.connect(new StdioClientTransport({
  command: process.execPath, args: ['--import', 'tsx', 'mcp/server.mjs'],
  cwd: process.cwd(), stderr: 'inherit', env: { ...process.env, DYB2_MCP_USER: 'codex' },
}));
async function call(name, project_id, args = {}) {
  const result = await client.callTool({ name, arguments: { project_id, ...args } }, undefined, { timeout: 300000 });
  if (result.isError) throw Error(`${name}: ${result.content.map(x => x.text).join('\n')}`);
  return JSON.parse(result.content[0].text);
}
async function allNotes(project_id, track) {
  const notes = [];
  for (let from_bar = 1; from_bar <= 32; from_bar += 8) {
    const view = await call('view_track', project_id, { track, from_bar, bars: 8, as: 'notes' });
    notes.push(...view.notes.map(note => ({ ...note, beat: (from_bar - 1) * 3 + note.beat })));
  }
  return notes;
}

for (const spec of [
  {
    id: '32550162e477d9e7', tempo: '90 bpm', part: 'Harp', leadNotes: 59,
    breakNotes: 232, bars: [1, 17], old: ['E4', 'G4', 'B4'], rise: ['B3', 'E4', 'G4'],
    name: 'B–E–G waltz within the harp accompaniment',
  },
  {
    id: 'a2ac7b7ae8fa8ad8', tempo: '82 bpm', part: 'Arp', leadNotes: 52,
    breakNotes: 192, bars: [1, 9, 25], old: ['A3', 'E4', 'C4'], rise: ['A3', 'C4', 'E4'],
    name: 'A–C–E rise within the forest arp',
  },
]) {
  const project = await call('open_project', spec.id);
  if (project.project_id !== spec.id || project.tempo !== spec.tempo ||
      project.meter !== '3/4' || project.bars !== 32) {
    throw Error(`${spec.id}: active project changed; inspect before editing`);
  }
  for (const [name, count] of [[spec.part, 96], ['Pad', 128], ['Night breakbeat', spec.breakNotes]]) {
    if (project.tracks.find(x => x.name === name)?.notes !== count)
      throw Error(`${spec.id}: ${name} accompaniment changed`);
  }
  const notes = await allNotes(spec.id, spec.part);
  if (notes.length !== 96) throw Error(`${spec.id}: expected 96 accompaniment notes`);
  for (const bar of spec.bars) {
    const start = (bar - 1) * 3;
    const phrase = [0, 1, 2].map(beat => notes.find(note => note.beat === start + beat));
    if (phrase.some(note => !note)) throw Error(`${spec.id}: missing bar ${bar} motif note`);
    const pitches = phrase.map(note => note.pitch);
    if (pitches.join(',') !== spec.old.join(',') && pitches.join(',') !== spec.rise.join(','))
      throw Error(`${spec.id}: bar ${bar} motif changed: ${pitches.join(',')}`);
    phrase.forEach((note, i) => { note.pitch = spec.rise[i]; });
  }
  await call('write_notes', spec.id, {
    track: spec.part, start_bar: 1, bars: 32, name: spec.name, notes,
  });
  const lead = project.tracks.find(x => x.name === 'Flute');
  if (lead) {
    if (lead.notes !== spec.leadNotes || lead.instrument !== 'Dexed')
      throw Error(`${spec.id}: foreground flute changed`);
    await call('remove_track', spec.id, { track: 'Flute' });
  }
  const updated = await call('get_project', spec.id);
  if (updated.tracks.some(x => x.name === 'Flute')) throw Error(`${spec.id}: foreground flute remains`);
  const analysis = await call('analyse_song', spec.id);
  if (analysis.problems?.length) throw Error(`${spec.id}: ${analysis.problems.join('; ')}`);
  console.log(JSON.stringify({ project_id: spec.id, removed: 'Flute',
    accompaniment: spec.part, rise: spec.rise.join('–'), bars: spec.bars,
    retainedNotes: updated.tracks.find(x => x.name === spec.part)?.notes,
    problems: analysis.problems, warnings: analysis.warnings }));
}
await client.close();
JS
