#!/bin/sh
# Compose the shared outdoor night score as an editable dybase2 MCP project.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const client = new Client({name:'valhallasc-night-score',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
async function call(name,args={}) {
  const r = await client.callTool({name,arguments:args},undefined,{timeout:300000});
  if (r.isError) throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);
  const data = JSON.parse(r.content[0].text);
  console.log(name,JSON.stringify(data).slice(0,260));
  return data;
}
const project = await call('create_project',{name:'Valhalla Night - Lanterns After Sundown',bpm:72,time_signature:'4/4',key:'E minor'});
const A = {project_id:project.project_id};
console.log('PROJECT_ID='+project.project_id);
for (const [name,instrument,preset,volume_db] of [
  ['Lantern pulse','dexed','MARIMBA',-25],
  ['Night flute','dexed','WHISTLE FLUTE',-22],
  ['Starlight bells','dexed','GLASS VIBES',-30],
  ['Quiet sky','dexed','GLASS PAD',-29],
  ['Earth beneath','dexed','WOOD BASS',-23],
]) await call('add_track',{name,instrument,preset,volume_db,...A});
const chords='Em C G D Em C G D Em C G D Em C G D Em C G D Em C D Em';
await call('write_chords',{track:'Earth beneath',start_bar:1,bars:24,progression:chords,style:'root_fifth',octave:2,velocity:48,...A});
await call('write_chords',{track:'Quiet sky',start_bar:1,bars:24,progression:chords,style:'block',register:52,velocity:35,...A});
await call('write_chords',{track:'Lantern pulse',start_bar:1,bars:24,progression:chords,style:'arp_updown',register:62,rate:1,velocity:44,...A});
const phrase=[
  [['E4',0,1.5],['G4',2,.75],['B4',3,.75]],
  [['G4',0,1],['E4',1.5,1],['D4',3,.75]],
  [['B4',0,1],['D5',1.5,.75],['B4',3,1]],
  [['A4',0,1.5],['F#4',2,.75],['E4',3,1]],
  [['G4',0,1],['B4',1.5,1],['E5',3,.75]],
  [['D5',0,1.25],['B4',2,.75],['G4',3,1]],
  [['A4',0,1.5],['G4',2,.75],['F#4',3,.75]],
  [['E4',0,1.5],['G4',2,.75],['E4',3,1]],
];
for (const [part,start,velocity] of [['First stars',1,48],['The long watch',9,58],['Before the dawn',17,47]]) {
  const notes=[];
  for(let bar=0;bar<8;bar++) for(const [pitch,beat,beats] of phrase[bar])
    notes.push({pitch,beat:bar*4+beat,beats,velocity});
  await call('write_notes',{track:'Night flute',start_bar:start,bars:8,notes,name:part,...A});
}
const bells=[];
for(let bar=0;bar<24;bar+=2) {
  const pitch=['E5','G5','B5','F#5'][Math.floor(bar/2)%4];
  bells.push({pitch,beat:bar*4+3,beats:.6,velocity:bar>=8&&bar<16?40:32});
}
await call('write_notes',{track:'Starlight bells',start_bar:1,bars:24,notes:bells,name:'Distant lamps',...A});
for (const [name,at_bar] of [['First stars',1],['The long watch',9],['Before the dawn',17]])
  await call('add_marker',{name,at_bar,...A});
await call('add_fx_return',{name:'Night air',effect:'sorkverb',...A});
for (const [track,level_db] of [['Night flute',-22],['Starlight bells',-25],['Quiet sky',-27]])
  await call('set_send',{track,fx_return:'Night air',level_db,...A});
for (const [track,volume_db,pan] of [
  ['Lantern pulse',-30,-.25], ['Night flute',-12,.10],
  ['Starlight bells',-16,.3], ['Quiet sky',-24,-.12], ['Earth beneath',-29,0],
]) await call('set_mix',{track,volume_db,pan,...A});
await call('analyse_song',A);
console.log('Render with scripts/render_night_song.sh '+project.project_id);
await client.close();
JS
