#!/bin/sh
# Remove the foreground parts from the active Rimeveil and Gloamfen night projects.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const client = new Client({ name: 'valhallasc-next-two-no-lead', version: '1' });
await client.connect(new StdioClientTransport({
  command: process.execPath, args: ['--import', 'tsx', 'mcp/server.mjs'],
  cwd: process.cwd(), stderr: 'inherit', env: { ...process.env, DYB2_MCP_USER: 'codex' },
}));
async function call(name, project_id, args = {}) {
  const result = await client.callTool({ name, arguments: { project_id, ...args } }, undefined, { timeout: 300000 });
  if (result.isError) throw Error(`${name}: ${result.content.map(x => x.text).join('\n')}`);
  return JSON.parse(result.content[0].text);
}

for (const spec of [
  {
    id: '4091d2184af5bf68', tempo: '88 bpm', meter: '6/8',
    lead: 'Lead', leadNotes: 72, keep: [['Bells', 96], ['Pad', 128], ['Night breakbeat', 244]],
    marker: ['Lead enters', 'Distant bells rise', 11],
  },
  {
    id: '631d2ccf54a0ea32', tempo: '90 bpm', meter: '4/4',
    lead: 'Flute', leadNotes: 68, keep: [['Lanterns', 64], ['Pad', 132], ['Night breakbeat', 284]],
    marker: ['Flute and frame drum', 'Lanterns and frame drum', 7],
  },
]) {
  const project = await call('open_project', spec.id);
  if (project.project_id !== spec.id || project.tempo !== spec.tempo ||
      project.meter !== spec.meter || project.bars !== 32) {
    throw Error(`${spec.id}: active project changed; inspect before editing`);
  }
  for (const [name, notes] of spec.keep) {
    const track = project.tracks.find(x => x.name === name);
    if (!track || track.notes !== notes) throw Error(`${spec.id}: ${name} accompaniment changed`);
  }
  const lead = project.tracks.find(x => x.name === spec.lead);
  if (lead) {
    if (lead.notes !== spec.leadNotes) throw Error(`${spec.id}: foreground part changed`);
    await call('remove_track', spec.id, { track: spec.lead });
  }
  const [oldName, newName, at_bar] = spec.marker;
  if (project.markers.includes(`bar ${at_bar}: ${oldName}`)) {
    await call('remove_marker', spec.id, { name: oldName });
    await call('add_marker', spec.id, { name: newName, at_bar });
  }
  const updated = await call('get_project', spec.id);
  if (updated.tracks.some(x => x.name === spec.lead)) throw Error(`${spec.id}: foreground part remains`);
  const analysis = await call('analyse_song', spec.id);
  if (analysis.problems?.length) throw Error(`${spec.id}: ${analysis.problems.join('; ')}`);
  console.log(JSON.stringify({ project_id: spec.id, removed: spec.lead,
    retained: spec.keep.map(([name, notes]) => `${name}: ${notes}`),
    bars: updated.bars, problems: analysis.problems, warnings: analysis.warnings }));
}
await client.close();
JS
