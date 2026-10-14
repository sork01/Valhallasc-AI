#!/bin/sh
# Compose the Rain Crown Temple - The Jade Monsoon editable score through dybase2's stdio MCP server.
set -eu
cd "$(dirname "$0")/../../dybase2"
exec /home/serveperry/.nvm/versions/node/v20.20.2/bin/node --input-type=module <<'JS'
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
const client=new Client({name:'valhallasc-rain_crown-score',version:'1'});
await client.connect(new StdioClientTransport({command:process.execPath,args:['--import','tsx','mcp/server.mjs'],cwd:process.cwd(),stderr:'inherit'}));
async function call(name,args={}){const r=await client.callTool({name,arguments:args},undefined,{timeout:240000});if(r.isError)throw Error(`${name}: ${r.content.map(x=>x.text).join('\n')}`);const data=JSON.parse(r.content[0].text);console.log(name,JSON.stringify(data).slice(0,260));return data;}
const project=await call('create_project',{name:'Valhalla Rain Crown Temple - The Jade Monsoon',bpm:76,time_signature:'4/4',key:'E minor'});
const A={project_id:project.project_id};console.log('PROJECT_ID='+project.project_id);
for(const [name,instrument,preset,volume_db] of [
 ['Water pulse','dexed','MARIMBA',-17],
 ['Rain voice','dexed','WHISTLE FLUTE',-19],
 ['Jade bells','dexed','GLASS VIBES',-26],
 ['Temple mist','dexed','GLASS PAD',-27],
 ['Flood bass','dexed','WOOD BASS',-17],
 ['Monsoon drums','dexed','LOG DRUM',-22],
])await call('add_track',{name,instrument,preset,volume_db,...A});
const chords='Em C Am B7 Em C Am B7 Em C Am B7 Em C Am B7 Em C Am B7 Em C Am B7 Em C Am B7 Em C Am B7';
await call('write_chords',{track:'Flood bass',start_bar:1,bars:32,progression:chords,style:'root_fifth',octave:2,velocity:72,...A});
await call('write_chords',{track:'Water pulse',start_bar:1,bars:32,progression:chords,style:'arp_updown',register:62,rate:1,velocity:65,...A});
await call('write_chords',{track:'Temple mist',start_bar:1,bars:32,progression:chords,style:'block',register:53,velocity:38,...A});
await call('write_chords',{track:'Jade bells',start_bar:9,bars:16,progression:chords.split(' ').slice(8,24).join(' '),style:'arp_updown',register:78,rate:1,velocity:38,...A});
const tune=[
 [['E4',0,1],['C5',1.25,.5],['G4',2,.75],['B4',3,.5]],
 [['G4',0,.75],['F4',1,.75],['C5',2,.5],['D4',3,1]],
 [['F4',0,.75],['A4',1,.5],['B4',2,1],['F4',3,.5]],
 [['G4',0,.5],['F4',.75,.5],['D4',1.5,1],['C5',3,.75]],
 [['D4',0,.75],['F4',1,.5],['A4',2,.75],['E5',3,.5]],
 [['E4',0,.75],['A4',1,.5],['F4',2,1],['C5',3,.5]],
 [['G4',0,.5],['B4',1,.75],['A4',2,1],['G4',3,.5]],
 [['F4',0,.5],['C5',1,.5],['D4',2,1],['D4',3,.75]],
];
for(const [section,start] of [[0,1],[1,9],[2,17],[3,25]]){
 const notes=[];for(let bar=0;bar<8;bar++)for(const [pitch,beat,beats] of tune[bar])notes.push({pitch,beat:bar*4+beat,beats,velocity:section===0?55:section===2?75:section===3?62:67});
 await call('write_notes',{track:'Rain voice',start_bar:start,bars:8,notes,name:['The first rainfall','The jade hall','The floodgate','The crown rises'][section],...A});
}
const knocks=[];for(let bar=0;bar<32;bar++){
 knocks.push({pitch:'A2',beat:bar*4,beats:.25,velocity:bar%8===0?75:57});
 knocks.push({pitch:'C3',beat:bar*4+2,beats:.2,velocity:bar>=8&&bar<28?52:39});
 if(bar>=16&&bar<28)knocks.push({pitch:'E3',beat:bar*4+3.5,beats:.15,velocity:34});
}
await call('write_notes',{track:'Monsoon drums',start_bar:1,bars:32,notes:knocks,name:'Root heartbeat',...A});
for(const [name,at_bar] of [['The first rainfall',1],['The jade hall',9],['The floodgate',17],['The crown rises',25]])await call('add_marker',{name,at_bar,...A});
await call('add_fx_return',{name:'Temple chamber',effect:'sorkverb',...A});
for(const [track,level_db] of [['Rain voice',-22],['Jade bells',-29],['Temple mist',-27]])await call('set_send',{track,fx_return:'Temple chamber',level_db,...A});
await call('analyse_song',A);
console.log('Score saved. Render with scripts/render_rain_crown_song.sh '+project.project_id);
await client.close();
JS
