#!/bin/sh
# Replace only the Hip-hop hi-hats with Chillhop hi-hats and remove foreground leads.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';

const songs = [
  ['stormglass', '7cfe6a386dd3266f', 'Night breakbeat', 'Breaker strings', [[2,10],[2,5,10,14],[2,5,10,14],[5,14]], [53,58,58,55]],
  ['sunward', 'd33fdacfd0720334', 'Night breakbeat', 'Hillside flute', [[2,10],[2,6,10,14],[2,6,10,14],[6,14]], [49,54,54,51]],
  ['ribbonwild', '5a0f5aed7413939b', 'Night breakbeat', 'Festival brass', [[2,10],[2,6,10,14],[2,6,10,14],[2,6,10,14]], [53,58,58,55]],
  ['tanglecrown', 'b9a83443f1d8b949', 'Night breakbeat', 'River flute', [[2,10],[2,6,10,14],[2,6,10,14],[2,6,10,14]], [51,56,56,53]],
  ['veyrroot', 'f72407011081b07f', 'Leaf-shaker break', 'Canopy flute', [[2,10],[2,6,10,14],[2,10,14],[6,14]], [50,55,55,52]],
];
const c = new Client({name:'valhallasc-late-night-hat-lead-repair',version:'1'});
await c.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit',env:{...process.env,DYB2_MCP_USER:'codex'}}));
async function call(name, args) {
  const r = await c.callTool({name,arguments:args},undefined,{timeout:300000});
  if (r.isError) throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);
  return JSON.parse(r.content[0].text);
}
for (const [zone, project_id, drums, lead, hats, velocities] of songs) {
  const project = await call('open_project',{project_id});
  if (project.project_id !== project_id) throw Error(`${zone}: opened a different project`);
  const drumTrack = project.tracks.find(t=>t.name===drums);
  if (!drumTrack || drumTrack.kind!=='drum') throw Error(`${zone}: missing drum track`);
  await call('set_preset',{project_id,track:drums,preset:'Hip-hop'});
  const hatTrack='Chillhop hi-hat';
  if (project.tracks.some(t=>t.name===hatTrack)) {
    await call('clear_bars',{project_id,track:hatTrack});
    await call('set_preset',{project_id,track:hatTrack,preset:'Chillhop'});
    await call('set_mix',{project_id,track:hatTrack,volume_db:-10});
  } else await call('add_track',{project_id,name:hatTrack,instrument:'axiom8',preset:'Chillhop',volume_db:-10});
  let addedHats = 0;
  for (const [section, from_bar] of [1,9,17,25].entries()) {
    const part = drumTrack.parts.find(p=>p.from_bar===from_bar);
    if (!part || part.to_bar!==from_bar+7) throw Error(`${zone}: unexpected drum section at bar ${from_bar}`);
    const original = (await call('view_track',{project_id,track:drums,from_bar,bars:8,as:'notes'})).notes;
    const notes = original.filter(n=>!['F#2','G#2','A#2'].includes(n.pitch));
    const hatNotes=[];
    for(let bar=0;bar<8;bar++) for(const step of hats[section]) {
      hatNotes.push({pitch:'F#2',beat:bar*4+step/4,beats:.225,velocity:velocities[section]});
      addedHats++;
    }
    await call('write_notes',{project_id,track:drums,start_bar:from_bar,bars:8,notes,name:part.name});
    await call('write_notes',{project_id,track:hatTrack,start_bar:from_bar,bars:8,notes:hatNotes,name:`${part.name} Chillhop hats`});
  }
  if (project.tracks.some(t=>t.name===lead)) await call('remove_track',{project_id,track:lead});
  const updated = await call('get_project',{project_id});
  if (updated.tracks.some(t=>t.name===lead)) throw Error(`${zone}: lead remains`);
  for (const [section, from_bar] of [1,9,17,25].entries()) {
    const original = (await call('view_track',{project_id,track:drums,from_bar,bars:8,as:'notes'})).notes;
    const replacements = (await call('view_track',{project_id,track:hatTrack,from_bar,bars:8,as:'notes'})).notes;
    if (original.some(n=>['F#2','G#2','A#2'].includes(n.pitch))) throw Error(`${zone}: Hip-hop hat remains in bar ${from_bar}`);
    if (replacements.length!==8*hats[section].length || replacements.some(n=>n.pitch!=='F#2')) throw Error(`${zone}: Chillhop hat mismatch in bar ${from_bar}`);
  }
  console.log(JSON.stringify({zone,project_id,hatPreset:'Chillhop',addedHats,leadRemoved:lead}));
}
await c.close();
JS
