#!/bin/sh
# Place each source call and its answer in a quiet accompaniment part.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const client = new Client({ name: 'valhallasc-astral-prism-no-lead', version: '1' });
await client.connect(new StdioClientTransport({
  command: process.execPath, args: ['--import', 'tsx', 'mcp/server.mjs'],
  cwd: process.cwd(), stderr: 'inherit', env: { ...process.env, DYB2_MCP_USER: 'codex' },
}));
async function call(name, project_id, args = {}) {
  const result = await client.callTool({ name, arguments: { project_id, ...args } }, undefined, { timeout: 300000 });
  if (result.isError) throw Error(`${name}: ${result.content.map(x => x.text).join('\n')}`);
  return JSON.parse(result.content[0].text);
}
async function allNotes(project_id, track, beatsPerBar) {
  const notes = [];
  for (let from_bar = 1; from_bar <= 32; from_bar += 8) {
    const view = await call('view_track', project_id, { track, from_bar, bars: 8, as: 'notes' });
    notes.push(...view.notes.map(note => ({ ...note, beat: (from_bar - 1) * beatsPerBar + note.beat })));
  }
  return notes;
}
function revoice(notes, beatsPerBar, phrase) {
  const start = (phrase.bar - 1) * beatsPerBar;
  const first = notes.find(note => note.beat === start + 1);
  const last = notes.find(note => note.beat === start + 3);
  if (!first || !last || notes.some(note => note.beat === start + 2))
    throw Error(`bar ${phrase.bar}: accompaniment grid changed`);
  const old = [first.pitch, last.pitch].join(',');
  if (old !== phrase.old.join(',') && old !== [phrase.pitches[0], phrase.pitches[2]].join(','))
    throw Error(`bar ${phrase.bar}: accompaniment pitches changed: ${old}`);
  first.pitch = phrase.pitches[0];
  last.pitch = phrase.pitches[2];
  notes.push({ pitch: phrase.pitches[1], beat: start + 2, beats: .45, velocity: 47 });
}

for (const spec of [
  {
    id: 'c452ba1d09acef9f', tempo: '96 bpm', meter: '5/4', beats: 5,
    part: 'Wood', lead: 'Melody', leadNotes: 53, breakNotes: 312,
    name: 'C#–E–F# wood call and falling B minor answer',
    phrases: [
      ...[[1, ['A3','E4']], [9, ['F#4','C#5']], [25, ['A3','E4']]]
        .map(([bar, old]) => ({ bar, old, pitches: ['C#4','E4','F#4'] })),
      ...[17, 29].map(bar => ({ bar, old: ['D4','A4'], pitches: ['F#4','D4','B3'] })),
    ],
  },
  {
    id: '5f35d1f41f52775f', tempo: '84 bpm', meter: '4/4', beats: 4,
    part: 'Salt glints', lead: 'Mirage call', leadNotes: 48, breakNotes: 252,
    name: 'E–F–G glass call and descending reflection',
    phrases: [
      ...[4, 20, 28].map(bar => ({ bar, old: ['A4','C5'], pitches: ['E4','F4','G4'] })),
      ...[8, 23].map(bar => ({ bar, old: ['A4','C5'], pitches: ['G4','F4','E4'] })),
    ],
  },
]) {
  const project = await call('open_project', spec.id);
  if (project.project_id !== spec.id || project.tempo !== spec.tempo ||
      project.meter !== spec.meter || project.bars !== 32) {
    throw Error(`${spec.id}: active project changed; inspect before editing`);
  }
  for (const [name, count] of [[spec.part, 64], ['Night breakbeat', spec.breakNotes]]) {
    if (project.tracks.find(track => track.name === name)?.notes !== count)
      throw Error(`${spec.id}: ${name} accompaniment changed`);
  }
  const notes = await allNotes(spec.id, spec.part, spec.beats);
  if (notes.length !== 64) throw Error(`${spec.id}: unexpected accompaniment note count`);
  for (const phrase of spec.phrases) revoice(notes, spec.beats, phrase);
  await call('write_notes', spec.id, {
    track: spec.part, start_bar: 1, bars: 32, name: spec.name, notes,
  });
  const lead = project.tracks.find(track => track.name === spec.lead);
  if (lead) {
    if (lead.notes !== spec.leadNotes || lead.instrument !== 'Sork-60')
      throw Error(`${spec.id}: foreground lead changed`);
    await call('remove_track', spec.id, { track: spec.lead });
  }
  const updated = await call('get_project', spec.id);
  if (updated.tracks.some(track => track.name === spec.lead))
    throw Error(`${spec.id}: foreground lead remains`);
  const analysis = await call('analyse_song', spec.id);
  if (analysis.problems?.length) throw Error(`${spec.id}: ${analysis.problems.join('; ')}`);
  console.log(JSON.stringify({ project_id: spec.id, removed: spec.lead,
    accompaniment: spec.part, motifBars: spec.phrases.map(phrase => phrase.bar),
    retainedNotes: updated.tracks.find(track => track.name === spec.part)?.notes,
    problems: analysis.problems, warnings: analysis.warnings }));
}
await client.close();
JS
