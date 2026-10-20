#!/bin/sh
# Remove the foreground parts from the active Greenmeadow and Crags night projects.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const client = new Client({ name: 'valhallasc-first-two-no-lead', version: '1' });
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
    id: '6c52c389c99ed898', tempo: '100 bpm', meter: '6/8',
    lead: 'Kantele', leadNotes: 42, keep: [['Harp', 96], ['Flute', 38], ['Night breakbeat', 248]],
    markers: [['Pass 1 - kantele', 'Pass 1 - harp and fireflies', 1]],
  },
  {
    id: '90d3be446ee5a58f', tempo: '92 bpm', meter: '4/4',
    lead: 'Lead', leadNotes: 74, keep: [['Arp', 96], ['Night breakbeat', 268]],
    markers: [
      ['Pass 1 - hushed lead', 'Pass 1 - ember plucks', 1],
      ['Pass 2 - snarling lead', 'Pass 2 - ember echoes', 17],
    ],
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
  for (const [oldName, newName, at_bar] of spec.markers) {
    if (project.markers.includes(`bar ${at_bar}: ${oldName}`)) {
      await call('remove_marker', spec.id, { name: oldName });
      await call('add_marker', spec.id, { name: newName, at_bar });
    }
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
