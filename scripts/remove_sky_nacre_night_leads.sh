#!/bin/sh
# Carry each source motif in the accompaniment before removing its lead track.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const client = new Client({ name: 'valhallasc-sky-nacre-no-lead', version: '1' });
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
function revoice(notes, beatsPerBar, bar, beats, allowed, replacement) {
  const phrase = beats.map(beat => notes.find(note => note.beat === (bar - 1) * beatsPerBar + beat));
  if (phrase.some(note => !note)) throw Error(`bar ${bar}: missing motif note`);
  const pitches = phrase.map(note => note.pitch).join(',');
  if (!allowed.some(p => p.join(',') === pitches) && replacement.join(',') !== pitches)
    throw Error(`bar ${bar}: accompaniment changed: ${pitches}`);
  phrase.forEach((note, i) => { note.pitch = replacement[i]; });
}

for (const spec of [
  {
    id: 'f8d95f2b7456bee1', tempo: '76 bpm', meter: '4/4', beats: 4,
    part: 'Arp', partNotes: 96, lead: 'Flute', leadNotes: 52, leadInstrument: 'Dexed',
    breakNotes: 196, name: 'A–F#–A sky ascent in the quiet arp',
    phrases: [1, 9, 25].map(bar => ({ bar, beats: [.5, 2, 3.5],
      allowed: [['D4', 'A4', 'C#5']], replacement: ['A3', 'F#4', 'A4'] })),
  },
  {
    id: 'f0c6df77cbbaed17', tempo: '90 bpm', meter: '6/8', beats: 3,
    part: 'Keys', partNotes: 64, lead: 'Melody', leadNotes: 43, leadInstrument: 'Sork-60',
    breakNotes: 192, name: 'A–C question and G–E reply in the quiet keys',
    phrases: [
      ...[1, 9, 25].map(bar => ({ bar, beats: [.5, 2],
        allowed: [['F4', 'A4'], ['A3', 'C4']], replacement: ['A3', 'C4'] })),
      ...[10, 26].map(bar => ({ bar, beats: [.5, 2],
        allowed: [['E4', 'G4']], replacement: ['G3', 'E4'] })),
    ],
  },
]) {
  const project = await call('open_project', spec.id);
  if (project.project_id !== spec.id || project.tempo !== spec.tempo ||
      project.meter !== spec.meter || project.bars !== 32) {
    throw Error(`${spec.id}: active project changed; inspect before editing`);
  }
  for (const [name, count] of [[spec.part, spec.partNotes], ['Night breakbeat', spec.breakNotes]]) {
    if (project.tracks.find(track => track.name === name)?.notes !== count)
      throw Error(`${spec.id}: ${name} accompaniment changed`);
  }
  const notes = await allNotes(spec.id, spec.part, spec.beats);
  if (notes.length !== spec.partNotes) throw Error(`${spec.id}: unexpected note count`);
  for (const phrase of spec.phrases)
    revoice(notes, spec.beats, phrase.bar, phrase.beats, phrase.allowed, phrase.replacement);
  await call('write_notes', spec.id, {
    track: spec.part, start_bar: 1, bars: 32, name: spec.name, notes,
  });
  const lead = project.tracks.find(track => track.name === spec.lead);
  if (lead) {
    if (lead.notes !== spec.leadNotes || lead.instrument !== spec.leadInstrument)
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
