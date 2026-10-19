#!/bin/sh
# Create Stormglass Shore's editable score through the dybase2 MCP server.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';

const client = new Client({name:'valhallasc-stormglass-score',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
async function call(name,args={}) {
  const result=await client.callTool({name,arguments:args},undefined,{timeout:240000});
  if(result.isError) throw Error(`${name}: ${result.content.map(x=>x.text).join('\n')}`);
  const data=JSON.parse(result.content[0].text);
  console.log(name,JSON.stringify(data).slice(0,240));
  return data;
}
const project=await call('create_project',{name:'Valhalla Stormglass Shore - Where the Breakers Sing',bpm:96,time_signature:'4/4',key:'E minor'});
const A={project_id:project.project_id};
console.log('PROJECT_ID='+project.project_id);
for(const [name,instrument,preset,volume_db] of [
  ['Undertow bass','sorkbass2','Fingered',-18],
  ['Sea mist','sork60','Swelling Choir',-24],
  ['Glass current','sork60','Arp Sequence',-24],
  ['Breaker strings','sork60','Juno Strings',-17],
  ['Storm bell','dexed','TUB BELLS',-24],
  ['Shore pulse','dexed','LOG DRUM',-23],
]) await call('add_track',{name,instrument,preset,volume_db,...A});
const chords=[
  'Em C G D Em C Am B7',
  'Em C G D Am C B7 Em',
  'C G D Em C Am B7 B7',
  'Em C G D Am C B7 Em',
].join(' ');
await call('write_chords',{track:'Undertow bass',start_bar:1,bars:32,progression:chords,style:'root_fifth',octave:2,velocity:77,...A});
await call('write_chords',{track:'Sea mist',start_bar:1,bars:32,progression:chords,style:'block',register:58,velocity:56,...A});
await call('write_chords',{track:'Glass current',start_bar:1,bars:32,progression:chords,style:'arp_updown',register:74,rate:.5,velocity:54,...A});
const motif=[
  [['E5',0,.75],['G5',1,.75],['B5',2,1.5]],
  [['G5',0,.75],['E5',1,.75],['D5',2,1.5]],
  [['D5',0,.75],['G5',1,.75],['B5',2,.75],['D6',3,.75]],
  [['A5',0,1],['F#5',1.5,.75],['E5',2.5,1]],
  [['E5',0,.75],['G5',1,.75],['B5',2,1.5]],
  [['C6',0,.75],['B5',1,.75],['G5',2,1.5]],
  [['A5',0,.75],['F#5',1,.75],['D#5',2,1]],
  [['E5',0,1.5],['B4',2,.75],['E5',3,.75]],
];
for(const [part,bar] of [[0,1],[1,9],[2,17],[3,25]]) {
  const notes=[];
  for(let i=0;i<8;i++) for(const [pitch,beat,beats] of motif[i])
    notes.push({pitch,beat:i*4+beat,beats,velocity:part===0?62:part===2?83:72});
  await call('write_notes',{track:'Breaker strings',start_bar:bar,bars:8,notes,name:['Salt wind','Glass tide','Lightning over the water','Safe harbor'][part],...A});
}
const bells=[];
for(let bar=0;bar<32;bar++) if(bar%2===0) {
  bells.push({pitch:bar%8===6?'B4':'E5',beat:bar*4,beats:.5,velocity:bar>=16&&bar<24?53:38});
  if(bar>=16&&bar<24) bells.push({pitch:'G5',beat:bar*4+2,beats:.5,velocity:42});
}
await call('write_notes',{track:'Storm bell',start_bar:1,bars:32,notes:bells,name:'Distant storm bell',...A});
const pulse=[];
for(let bar=0;bar<32;bar++) {
  pulse.push({pitch:'E2',beat:bar*4,beats:.3,velocity:bar%8===0?75:59});
  pulse.push({pitch:'B2',beat:bar*4+2,beats:.25,velocity:bar>=16&&bar<24?62:48});
}
await call('write_notes',{track:'Shore pulse',start_bar:1,bars:32,notes:pulse,name:'Breaking surf pulse',...A});
for(const [name,at_bar] of [['The salt shore',1],['Glassray waters',9],['The storm front',17],['Lights at the harbor',25]])
  await call('add_marker',{name,at_bar,...A});
await call('add_fx_return',{name:'Coastal air',effect:'sorkverb',...A});
for(const [track,level_db] of [['Breaker strings',-20],['Sea mist',-23],['Storm bell',-25]])
  await call('set_send',{track,fx_return:'Coastal air',level_db,...A});
await call('analyse_song',A);
await client.close();
JS
